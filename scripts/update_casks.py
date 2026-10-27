"""Update simple GitHub Release Casks and generate the README application tables."""

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import signal
import tempfile
from urllib.parse import quote, unquote, urlsplit

TAP = "Axolotl-Launcher/tap"
VERSION = re.compile(r'(?m)^  version "([0-9]+(?:\.[0-9]+)+)"[ \t]*$')
SHA256 = re.compile(r'(?m)^  sha256 "([0-9a-f]{64})"[ \t]*$')
COMPLEX = re.compile(r'^\s*(?:arch\b|on_[a-z_]+\b|if\b|unless\b|case\b|language\b|depends_on\s+arch:\s*\{|version\s+:|sha256\s+:|url\s+do\b)', re.M)


class Unsupported(ValueError):
    """A Cask requires manual updates rather than guessed release information."""


def run(*args, timeout=600):
    # Argument vectors go directly to the process; shell escaping would alter them.
    return subprocess.check_output(args, text=True, timeout=timeout)


def metadata(token):
    data = json.loads(run("brew", "info", "--cask", "--json=v2", f"{TAP}/{token}"))
    casks = data.get("casks", [])
    if len(casks) != 1 or casks[0].get("token") != token:
        raise ValueError(f"Unexpected Homebrew metadata for {token}")
    return casks[0]


def release_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query or parsed.fragment:
        raise Unsupported("Requires an HTTPS GitHub Releases download URL")
    parts = parsed.path.split("/")
    if len(parts) != 7 or parts[3:5] != ["releases", "download"]:
        raise Unsupported("Requires /owner/repo/releases/download/tag/asset")
    owner, repo, tag, asset = map(unquote, (parts[1], parts[2], parts[5], parts[6]))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
        raise Unsupported("Unsupported GitHub repository name")
    if not tag or not asset or "/" in asset or any(c in tag + asset for c in "\r\n\x00"):
        raise Unsupported("Invalid release tag or asset")
    return f"{owner}/{repo}", tag, asset


def simple_source(source, info):
    # Only literal, top-level version/SHA256 fields are rewritten in this first version.
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    if (COMPLEX.search(code) or len(re.findall(r'^\s*version\b', code, re.M)) != 1
            or len(re.findall(r'^\s*sha256\b', code, re.M)) != 1
            or len(re.findall(r'^  url\b', code, re.M)) != 1
            or not re.search(r'^  url "[^\n]+"\s*$', code, re.M)
            or not re.search(r'^  livecheck do\s*$', code, re.M)
            or any(expr != "version" for expr in re.findall(r"#\{([^}]+)\}", code))):
        raise Unsupported("Requires simple version/SHA256/URL fields and explicit livecheck")
    version, checksum = VERSION.search(code), SHA256.search(code)
    if not version or not checksum or info.get("version") != version[1] or info.get("sha256") != checksum[1]:
        raise Unsupported("Requires one numeric version and one literal SHA256")
    if info.get("languages") or info.get("disabled") or info.get("deprecated") or info.get("skip_livecheck"):
        raise Unsupported("Language-specific, disabled, deprecated or skipped Cask")
    release_url(info["url"])
    return version[1]


def latest_version(token, current):
    data = json.loads(run("brew", "livecheck", "--cask", "--json", f"{TAP}/{token}"))
    if not isinstance(data, list) or len(data) != 1 or data[0].get("cask") != token:
        raise ValueError(f"Unexpected livecheck result for {token}")
    version = data[0].get("version", {})
    latest, outdated = version.get("latest"), version.get("outdated")
    if type(outdated) is not bool:
        raise ValueError(f"Missing livecheck version status for {token}: {data}")
    if not isinstance(latest, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", latest):
        raise Unsupported("Latest release has an unsupported version format")
    if outdated and tuple(map(int, latest.split("."))) <= tuple(map(int, current.split("."))):
        raise ValueError(f"Livecheck would downgrade or repeat {token}: {latest}")
    return latest if outdated else None


def checksum_for_release(url, repository, tag):
    release = json.loads(run("gh", "api", f"repos/{repository}/releases/tags/{quote(tag, safe='')}"))
    if release.get("tag_name") != tag or release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError(f"Not a stable official release: {repository} {tag}")
    assets = [a for a in release.get("assets", []) if a.get("browser_download_url") == url]
    if len(assets) != 1:
        raise ValueError(f"Expected exactly one official release asset: {url}")
    with tempfile.TemporaryDirectory(prefix="cask-download-") as directory:
        archive = Path(directory) / "asset"
        run("curl", "--fail", "--location", "--retry", "3",
            "--connect-timeout", "20", "--max-time", "300", "--retry-max-time", "480", "--proto", "=https",
            "--proto-redir", "=https", "--output", str(archive), url)
        checksum = file_hash(archive)
    digest = assets[0].get("digest")
    if digest and digest != f"sha256:{checksum}":
        raise ValueError(f"Checksum differs from upstream digest: {url}")
    return checksum


def atomic_write(path, content):
    """Replace one file without exposing truncated contents; preserve its mode."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content.encode("utf-8") if isinstance(content, str) else content)
        temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_changes(changes, originals, validate=None):
    """Reject intervening edits and roll back completed writes on normal failure."""
    changes = {path: value.encode("utf-8") if isinstance(value, str) else value for path, value in changes.items()}
    originals = {path: value.encode("utf-8") if isinstance(value, str) else value for path, value in originals.items()}
    for path, original in originals.items():
        if path.read_bytes() != original:
            raise ValueError(f"File changed during update; preserving it: {path}")
    written = []
    try:
        for path, content in changes.items():
            if path.read_bytes() != originals[path]:
                raise ValueError(f"File changed during update; preserving it: {path}")
            if content != originals[path]:
                atomic_write(path, content)
                written.append(path)
        if validate is not None:
            validate()
    except BaseException:
        for path in reversed(written):
            # Never undo an external edit made after our own replacement.
            if path.read_bytes() == changes[path]:
                atomic_write(path, originals[path])
        raise


def candidate(path, info):
    source = path.read_text()
    current = simple_source(source, info)
    latest = latest_version(path.stem, current)
    if latest is None:
        print(f"{path.stem} is up to date")
        return source
    provisional = VERSION.sub(lambda _: f'  version "{latest}"', source, count=1)
    try:
        atomic_write(path, provisional)
        resolved = metadata(path.stem)
    finally:
        if path.read_text() != provisional:
            raise ValueError(f"Cask changed during version resolution; preserving it: {path}")
        atomic_write(path, source)
    if resolved["version"] != latest:
        raise ValueError(f"Homebrew did not resolve the new version for {path.stem}")
    old_repo, _, _ = release_url(info["url"])
    repository, tag, _ = release_url(resolved["url"])
    if repository != old_repo:
        raise ValueError(f"Download repository changed for {path.stem}")
    if resolved["url"] == info["url"]:
        raise Unsupported("Download URL does not change with the version")
    checksum = checksum_for_release(resolved["url"], repository, tag)
    print(f"Updating {path.stem}: {current} -> {latest}")
    return SHA256.sub(lambda _: f'  sha256 "{checksum}"', provisional, count=1)


def markdown_text(value):
    text = html.escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`*_|\[\]])", r"\\\1", text)


def readme_tables(readme, casks):
    rows = []
    for token, info in sorted(casks.items()):
        name = markdown_text(info["name"][0])
        desc = markdown_text(info.get("desc") or "")
        homepage = info["homepage"]
        if urlsplit(homepage).scheme not in ("http", "https"):
            raise ValueError(f"Invalid homepage for {token}")
        homepage = quote(homepage, safe=":/?#=&%+@!~;,$-._")
        rows.append(f"| [{name}]({homepage}) | {desc} | `brew install --cask {TAP}/{token}` |")
    for language, header in (("zh", "| 应用 | 简介 | 安装命令 |"),
                             ("en", "| Application | Description | Installation |")):
        start, end = f"<!-- casks:{language}:start -->", f"<!-- casks:{language}:end -->"
        if readme.count(start) != 1 or readme.count(end) != 1:
            raise ValueError(f"README must contain exactly one {language} table marker pair")
        block = "\n".join([start, header, "|---|---|---|", *rows, end])
        pattern = re.escape(start) + r".*?" + re.escape(end)
        readme, count = re.subn(pattern, lambda _: block, readme, flags=re.S)
        if count != 1:
            raise ValueError(f"Invalid README marker order: {language}")
    return readme


def update(root, readme_only=False):
    paths = sorted((root / "Casks").glob("*.rb"))
    if not paths:
        raise ValueError("No Casks found")
    changes, casks = {}, {}
    readme = root / "README.md"
    originals = {path: path.read_text() for path in [*paths, readme]}
    for path in paths:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", path.stem) or path.is_symlink():
            raise ValueError(f"Invalid Cask path: {path}")
        info = metadata(path.stem)
        casks[path.stem] = info
        if not readme_only:
            try:
                changes[path] = candidate(path, info)
            except Unsupported as error:
                print(f"::warning::{path.stem}: {error}; leaving Cask unchanged")
    changes[readme] = readme_tables(originals[readme], casks)
    write_changes(changes, originals)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_content(root):
    files = run("git", "-C", str(root), "ls-files", "-z").rstrip("\x00").split("\x00")
    result = {}
    for name in files:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or symlinked tracked file: {name}")
        result[name] = [file_hash(path), bool(path.stat().st_mode & 0o111)]
    return result


def snapshot(root):
    base = run("git", "-C", str(root), "rev-parse", "HEAD").strip()
    changed = run("git", "-C", str(root), "diff", "--name-only", "-z", base).rstrip("\x00")
    changes = sorted(changed.split("\x00")) if changed else []
    if any(name != "README.md" and not re.fullmatch(r"Casks/[^/]+\.rb", name) for name in changes):
        raise ValueError("Update contains unexpected changed files")
    return {"base": base, "changes": changes, "files": tracked_content(root)}


def verify(root, proposal):
    expected = json.loads((proposal / "manifest.json").read_text())
    if tracked_content(root) != expected["files"]:
        raise ValueError("PR content differs from the validated update proposal")
    changed = run("git", "-C", str(root), "diff", "--name-only", "-z", expected["base"], "HEAD").rstrip("\x00")
    actual = sorted(changed.split("\x00")) if changed else []
    if not actual or actual != expected["changes"]:
        raise ValueError("PR changed-file list differs from the update proposal")
    print("PR files and contents match the expected update")


def export_proposal(root, proposal):
    proposal.mkdir(parents=True)
    expected = snapshot(root)
    (proposal / "manifest.json").write_text(json.dumps(expected))
    for name in expected["changes"]:
        target = proposal / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)


def apply_proposal(root, proposal):
    """Copy only audited data into a trusted checkout, without loading Cask Ruby."""
    if proposal.is_symlink() or any(path.is_symlink() for path in proposal.rglob("*")):
        raise ValueError("Proposal must not contain symlinks")
    expected = json.loads((proposal / "manifest.json").read_text())
    if run("git", "-C", str(root), "rev-parse", "HEAD").strip() != expected["base"]:
        raise ValueError("Proposal base differs from the publishing checkout")
    changes = expected["changes"]
    current = tracked_content(root)
    originals = {root / name: (root / name).read_bytes() for name in current}
    if any(hashlib.sha256(content).hexdigest() != current[path.relative_to(root).as_posix()][0]
           for path, content in originals.items()):
        raise ValueError("Files changed while reading the publishing checkout")
    allowed = {name for name in current if name == "README.md" or re.fullmatch(r"Casks/[a-z0-9][a-z0-9-]*\.rb", name)}
    if not isinstance(changes, list) or len(changes) != len(set(changes)) or not set(changes) <= allowed:
        raise ValueError("Proposal contains unexpected changed files")
    actual = {path.relative_to(proposal).as_posix() for path in proposal.rglob("*") if path.is_file()}
    if actual != set(changes) | {"manifest.json"}:
        raise ValueError("Proposal contains unexpected artifact files")
    if set(current) != set(expected["files"]) or any(
        value != expected["files"][name] for name, value in current.items() if name not in changes
    ):
        raise ValueError("Proposal changes files outside the allowed update")
    for name in changes:
        path = proposal / name
        if file_hash(path) != expected["files"][name][0] or current[name][1] != expected["files"][name][1]:
            raise ValueError(f"Proposal content or mode differs from the audit: {name}")
    changes_by_path = {root / name: (proposal / name).read_bytes() for name in changes}
    def validate_applied():
        if tracked_content(root) != expected["files"]:
            raise ValueError("Applied proposal differs from the audited contents")
    write_changes(changes_by_path, originals, validate=validate_applied)
    print("Audited proposal applied without evaluating Cask Ruby")


def interrupted(signum, _frame):
    raise SystemExit(128 + signum)


def main():
    # SIGTERM must unwind the temporary version edit, just like Ctrl-C.
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("update", "readme", "export", "apply", "verify"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--proposal", type=Path)
    args = parser.parse_args()
    if args.command in ("update", "readme"):
        update(args.root, readme_only=args.command == "readme")
    else:
        if args.proposal is None:
            parser.error("--proposal is required")
        {"export": export_proposal, "apply": apply_proposal, "verify": verify}[args.command](args.root, args.proposal)


if __name__ == "__main__":
    main()
