import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("updater", Path(__file__).resolve().parents[1] / "scripts/update_casks.py")
if SPEC is None or SPEC.loader is None:
    raise ImportError("Cannot load scripts/update_casks.py for tests")
u = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(u)

SOURCE = '''cask "sample" do
  version "1.0.0"
  sha256 "AAAAAAAA"
  url "https://github.com/example/sample/releases/download/v#{version}/sample-#{version}.dmg"
  name "Sample"
  desc "Example application"
  homepage "https://github.com/example/sample"
  livecheck do
    url :url
    strategy :github_latest
  end
end
'''.replace("AAAAAAAA", "a" * 64)
README = "Before\n<!-- casks:zh:start -->\nold\n<!-- casks:zh:end -->\nMiddle\n<!-- casks:en:start -->\nold\n<!-- casks:en:end -->\nAfter\n"


def info(token="sample", version="1.0.0", prefix="v"):
    return {"token": token, "version": version, "sha256": "a" * 64,
            "url": f"https://github.com/example/{token}/releases/download/{prefix}{version}/{token}-{version}.dmg",
            "name": [token], "desc": "Example application", "homepage": f"https://github.com/example/{token}"}


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "Casks").mkdir()
        self.path = self.root / "Casks/sample.rb"
        self.path.write_text(SOURCE)
        (self.root / "README.md").write_text(README)

    def test_subprocess_deadline_and_literal_arguments(self):
        with patch.object(subprocess, "check_output", return_value="ok") as execute:
            self.assertEqual(u.run("tool", "argument"), "ok")
            execute.assert_called_once_with(("tool", "argument"), text=True, timeout=600)
        with self.assertRaises(subprocess.TimeoutExpired):
            u.run(sys.executable, "-c", "import time; time.sleep(5)", timeout=0.02)
        marker = self.root / "should-not-exist"
        payload = f"; touch {marker}; $(touch {marker})"
        result = u.run(sys.executable, "-c", "import sys; print(sys.argv[1])", payload)
        self.assertEqual(result.strip(), payload)
        self.assertFalse(marker.exists())

    def proposal_git(self, *args):
        self.assertEqual(args[0], "git", "Publishing must not invoke Homebrew or Cask Ruby")
        if "rev-parse" in args:
            return "base\n"
        if "ls-files" in args:
            return "Casks/sample.rb\x00README.md\x00"
        if "diff" in args:
            return "Casks/sample.rb\x00"
        raise AssertionError(args)

    def make_proposal(self):
        proposal = self.root / "proposal"
        new_source = SOURCE.replace('version "1.0.0"', 'version "1.1.0"')
        self.path.write_text(new_source)
        with patch.object(u, "run", side_effect=self.proposal_git):
            u.export_proposal(self.root, proposal)
        self.path.write_text(SOURCE)
        return proposal, new_source

    def test_export_apply_and_verify_without_cask_execution(self):
        proposal, new_source = self.make_proposal()
        with patch.object(u, "run", side_effect=self.proposal_git):
            u.apply_proposal(self.root, proposal)
            self.assertEqual(self.path.read_text(), new_source)
            self.assertEqual((self.root / "README.md").read_text(), README)
            u.verify(self.root, proposal)

    def test_apply_rejects_edits_after_preflight_snapshot(self):
        proposal, _ = self.make_proposal()
        original_snapshot = u.tracked_content
        edited = SOURCE + "# concurrent edit\n"
        def snapshot_then_edit(root):
            current = original_snapshot(root)
            self.path.write_text(edited)
            return current
        with patch.object(u, "run", side_effect=self.proposal_git), patch.object(u, "tracked_content", side_effect=snapshot_then_edit):
            with self.assertRaisesRegex(ValueError, "Files changed"):
                u.apply_proposal(self.root, proposal)
        self.assertEqual(self.path.read_text(), edited)

    def test_apply_rolls_back_when_other_tracked_file_changes(self):
        proposal, _ = self.make_proposal()
        real_write = u.atomic_write
        readme = self.root / "README.md"
        edited_readme = README + "Maintainer edit\n"
        def edit_after_write(path, content):
            real_write(path, content)
            if path == self.path:
                readme.write_text(edited_readme)
        with patch.object(u, "run", side_effect=self.proposal_git), patch.object(u, "atomic_write", side_effect=edit_after_write):
            with self.assertRaisesRegex(ValueError, "Applied proposal differs"):
                u.apply_proposal(self.root, proposal)
        self.assertEqual(self.path.read_text(), SOURCE)
        self.assertEqual(readme.read_text(), edited_readme)

    def test_empty_proposal_is_a_noop(self):
        proposal = self.root / "proposal"
        def fake_git(*args):
            if "diff" in args:
                return ""
            return self.proposal_git(*args)
        with patch.object(u, "run", side_effect=fake_git):
            u.export_proposal(self.root, proposal)
            self.assertEqual([p.name for p in proposal.iterdir()], ["manifest.json"])
            u.apply_proposal(self.root, proposal)
        self.assertEqual(self.path.read_text(), SOURCE)

    def test_proposal_rejects_injection_tampering_base_and_modes(self):
        proposal, new_source = self.make_proposal()
        manifest = proposal / "manifest.json"
        expected = json.loads(manifest.read_text())
        cases = [
            dict(expected, base="other-base"),
            dict(expected, changes=["scripts/update_casks.py"]),
            dict(expected, changes=["../escape.rb"]),
            dict(expected, changes=["Casks/sample.rb"] * 2),
        ]
        for changed_name in ("Casks/sample.rb", "README.md"):
            changed = copy.deepcopy(expected)
            changed["files"][changed_name][0] = "b" * 64
            cases.append(changed)
        changed = copy.deepcopy(expected)
        changed["files"]["Casks/sample.rb"][1] = True
        cases.append(changed)
        with patch.object(u, "run", side_effect=self.proposal_git):
            for case in cases:
                manifest.write_text(json.dumps(case))
                with self.subTest(case=case), self.assertRaises(ValueError):
                    u.apply_proposal(self.root, proposal)
                self.assertEqual(self.path.read_text(), SOURCE)
            manifest.write_text(json.dumps(expected))
            injected = proposal / "injected.py"
            injected.write_text("must not be copied or executed")
            with self.assertRaises(ValueError):
                u.apply_proposal(self.root, proposal)
            injected.unlink()
            asset = proposal / "Casks/sample.rb"
            asset.write_text("tampered")
            with self.assertRaises(ValueError):
                u.apply_proposal(self.root, proposal)
            asset.unlink()
            asset.symlink_to(self.path)
            with self.assertRaises(ValueError):
                u.apply_proposal(self.root, proposal)
            self.assertEqual(self.path.read_text(), SOURCE)
            self.assertEqual((self.root / "README.md").read_text(), README)

    def test_release_url_formats(self):
        for tag in ("1.2.3", "v1.2.3", "release-1.2.3"):
            url = f"https://github.com/example/sample/releases/download/{tag}/sample.dmg"
            self.assertEqual(u.release_url(url), ("example/sample", tag, "sample.dmg"))
        self.assertEqual(u.release_url("https://github.com/example/sample/releases/download/v1.0/Some%20App.dmg")[2], "Some App.dmg")
        for url in ("http://github.com/a/b/releases/download/v1/file", "https://github.com.evil/a/b/releases/download/v1/file",
                    "https://example.com/a.dmg", "https://github.com/a/b/releases/latest/download/a.dmg",
                    "https://github.com/a/b/releases/download/v1/a.dmg?token=secret"):
            with self.subTest(url=url), self.assertRaises(u.Unsupported):
                u.release_url(url)

    def test_source_restrictions(self):
        self.assertEqual(u.simple_source(SOURCE, info()), "1.0.0")
        self.assertEqual(u.simple_source(SOURCE.replace("    url :url\n", ""), info()), "1.0.0")
        examples = [SOURCE.replace('  version "1.0.0"', '  version "1.0.0,2"'),
                    SOURCE.replace('  version "1.0.0"', '  version :latest'),
                    SOURCE.replace('  version "1.0.0"', '  on_arm do\n    version "1.0.0"\n  end'),
                    SOURCE.replace('  livecheck do', '  language "en" do'),
                    SOURCE.replace('  livecheck do', '  if OS.mac?\n  livecheck do'),
                    SOURCE.replace('#{version}', '#{arch}'),
                    SOURCE + '\n  sha256 "' + 'b' * 64 + '"\n']
        for source in examples:
            with self.subTest(source=source), self.assertRaises(u.Unsupported):
                u.simple_source(source, info())

    def test_livecheck_result(self):
        def data(latest, outdated):
            return json.dumps([{"cask": "sample", "version": {"latest": latest, "outdated": outdated}}])
        for latest, outdated, expected in [("1.0.0", False, None), ("1.1.0", True, "1.1.0")]:
            with patch.object(u, "run", return_value=data(latest, outdated)):
                self.assertEqual(u.latest_version("sample", "1.0.0"), expected)
        for value in ("[]", data("1.1.0", "true"), data("0.9.0", True), data("1.0.0", True)):
            with patch.object(u, "run", return_value=value), self.assertRaises(ValueError):
                u.latest_version("sample", "1.0.0")
        with patch.object(u, "run", return_value=data("1.1.0-beta", True)), self.assertRaises(u.Unsupported):
            u.latest_version("sample", "1.0.0")

    def test_candidate_updates_and_restores(self):
        new_info = info(version="1.1.0", prefix="release-")
        with patch.object(u, "latest_version", return_value="1.1.0"), patch.object(u, "metadata", return_value=new_info), patch.object(u, "checksum_for_release", return_value="b" * 64) as download:
            result = u.candidate(self.path, info())
        self.assertIn('version "1.1.0"', result)
        self.assertIn('sha256 "' + 'b' * 64 + '"', result)
        self.assertEqual(self.path.read_text(), SOURCE)
        download.assert_called_once_with(new_info["url"], "example/sample", "release-1.1.0")

    def test_atomic_write_failure_keeps_original_and_mode(self):
        self.path.chmod(0o640)
        with patch.object(u.os, "replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                u.atomic_write(self.path, "replacement")
        self.assertEqual(self.path.read_text(), SOURCE)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])
        u.atomic_write(self.path, "replacement")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o640)

    def test_final_write_failure_and_interrupt_roll_back(self):
        readme = self.root / "README.md"
        for error in (OSError("disk full"), KeyboardInterrupt(), SystemExit(143)):
            real_write = u.atomic_write
            def fail_second(path, content):
                if path == readme:
                    raise error
                real_write(path, content)
            with patch.object(u, "atomic_write", side_effect=fail_second):
                with self.assertRaises(type(error)):
                    u.write_changes({self.path: "new Cask", readme: "new README"},
                                    {self.path: SOURCE, readme: README})
            self.assertEqual(self.path.read_text(), SOURCE)
            self.assertEqual(readme.read_text(), README)

    def test_external_edits_are_preserved(self):
        edited = SOURCE + "# maintainer edit\n"
        def edit_during_resolution(_token):
            self.path.write_text(edited)
            return info(version="1.1.0")
        with patch.object(u, "latest_version", return_value="1.1.0"), patch.object(u, "metadata", side_effect=edit_during_resolution):
            with self.assertRaisesRegex(ValueError, "preserving"):
                u.candidate(self.path, info())
        self.assertEqual(self.path.read_text(), edited)
        with self.assertRaisesRegex(ValueError, "preserving"):
            u.write_changes({self.path: "new"}, {self.path: SOURCE})
        self.assertEqual(self.path.read_text(), edited)
        readme = self.root / "README.md"
        real_write = u.atomic_write
        def concurrent_write(path, content):
            if path == readme:
                self.path.write_text(edited)
                raise OSError("disk full")
            real_write(path, content)
        self.path.write_text(SOURCE)
        with patch.object(u, "atomic_write", side_effect=concurrent_write), self.assertRaises(OSError):
            u.write_changes({self.path: "new", readme: "new"}, {self.path: SOURCE, readme: README})
        self.assertEqual(self.path.read_text(), edited)

    def test_commented_fields_are_not_rewritten(self):
        commented = SOURCE.replace('  version "1.0.0"', '  # version "0.9.0"\n  version "1.0.0"')
        commented = commented.replace('  sha256 "', '  # sha256 "' + 'c' * 64 + '"\n  sha256 "', 1)
        self.path.write_text(commented)
        with patch.object(u, "latest_version", return_value="1.1.0"), patch.object(u, "metadata", return_value=info(version="1.1.0")), patch.object(u, "checksum_for_release", return_value="b" * 64):
            proposal = u.candidate(self.path, info())
        self.assertIn('  # version "0.9.0"', proposal)
        self.assertIn('  # sha256 "' + 'c' * 64 + '"', proposal)
        self.assertIn('  version "1.1.0"', proposal)
        self.assertIn('  sha256 "' + 'b' * 64 + '"', proposal)
        self.assertEqual(self.path.read_text(), commented)

    def test_dispatch_wait_requires_matching_successful_pr_commit(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/update.yml").read_text()
        step = workflow.split("      - name: Run CI on verified update PR\n", 1)[1].split("      - name: Merge", 1)[0]
        script = "\n".join(line[10:] for line in step.split("        run: |\n", 1)[1].splitlines())
        bin_path = self.root / "bin"
        bin_path.mkdir()
        gh = bin_path / "gh"
        gh.write_text('''#!/bin/sh
case "$1 $2" in
  "workflow run") exit 0 ;;
  "run list") printf '[{"databaseId":123,"headSha":"%s","createdAt":"9999-01-01T00:00:00Z"}]' "$FAKE_HEAD" ;;
  "run watch") echo "$*" >> "$WATCH_LOG"; exit "$WATCH_RESULT" ;;
  "run view") printf '{"headSha":"%s","conclusion":"%s"}' "$FAKE_HEAD" "$FINAL_CONCLUSION" ;;
  *) exit 99 ;;
esac
''')
        gh.chmod(0o755)
        for name, content in (("sleep", "#!/bin/sh\nexit 0\n"),
                              ("timeout", '#!/bin/sh\nshift\nexec "$@"\n')):
            command = bin_path / name
            command.write_text(content)
            command.chmod(0o755)
        log = self.root / "watch.log"
        environment = dict(os.environ, PATH=str(bin_path) + os.pathsep + os.environ["PATH"],
                           GH_TOKEN="fake", PR_HEAD="verified", GITHUB_REPOSITORY="example/tap", WATCH_LOG=str(log))
        for head, conclusion, final, success in (("verified", "0", "success", True), ("verified", "1", "failure", False),
                                                 ("verified", "124", "timed_out", False), ("different", "0", "success", False),
                                                 ("verified", "0", "skipped", False), ("verified", "0", "cancelled", False)):
            log.unlink(missing_ok=True)
            result = subprocess.run(["bash", "-c", script], env=dict(environment, FAKE_HEAD=head, WATCH_RESULT=conclusion, FINAL_CONCLUSION=final),
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode == 0, success, result.stderr)
            self.assertEqual(log.exists(), head == "verified")

    def test_existing_cask_release_patterns(self):
        root = Path(__file__).resolve().parents[1]
        for original in sorted((root / "Casks").glob("*.rb")):
            source = original.read_text()
            current = u.VERSION.search(source)[1]
            checksum = u.SHA256.search(source)[1]
            url_template = next(line.strip()[5:-1] for line in source.splitlines() if line.startswith('  url "'))
            old = info(original.stem, current)
            old.update(sha256=checksum, url=url_template.replace("#{version}", current))
            new = dict(old, version="9.9.9", url=url_template.replace("#{version}", "9.9.9"))
            path = self.root / "Casks" / original.name
            path.write_text(source)
            with self.subTest(token=original.stem), patch.object(u, "latest_version", return_value="9.9.9"), patch.object(u, "metadata", return_value=new), patch.object(u, "checksum_for_release", return_value="b" * 64) as download:
                proposal = u.candidate(path, old)
                self.assertIn('version "9.9.9"', proposal)
                self.assertEqual(source, path.read_text())
                repository, tag, _ = u.release_url(new["url"])
                download.assert_called_once_with(new["url"], repository, tag)

    def test_parse_error_and_interrupt_restore_original(self):
        for error in (RuntimeError("parse failed"), subprocess.TimeoutExpired("brew", 600), KeyboardInterrupt(), SystemExit(143)):
            with patch.object(u, "latest_version", return_value="1.1.0"), patch.object(u, "metadata", side_effect=error):
                with self.assertRaises(type(error)):
                    u.candidate(self.path, info())
            self.assertEqual(self.path.read_text(), SOURCE)

    def test_fixed_url_and_repository_change(self):
        fixed = info(version="1.1.0")
        fixed["url"] = info()["url"]
        changed = info(version="1.1.0")
        changed["url"] = changed["url"].replace("example/sample", "other/sample")
        for metadata, error in [(fixed, u.Unsupported), (changed, ValueError)]:
            with patch.object(u, "latest_version", return_value="1.1.0"), patch.object(u, "metadata", return_value=metadata), patch.object(u, "checksum_for_release") as download:
                with self.assertRaises(error):
                    u.candidate(self.path, info())
                download.assert_not_called()
            self.assertEqual(self.path.read_text(), SOURCE)

    def test_download_release_guards(self):
        url = info()["url"]
        release = {"tag_name": "v1.0.0", "draft": False, "prerelease": False,
                   "assets": [{"browser_download_url": url}]}
        def fake_run(*args):
            if args[0] == "gh":
                return json.dumps(current)
            if args[0] == "curl":
                Path(args[args.index("--output") + 1]).write_bytes(b"official asset")
                return ""
            raise AssertionError(args)
        current = copy.deepcopy(release)
        with patch.object(u, "run", side_effect=fake_run):
            checksum = u.checksum_for_release(url, "example/sample", "v1.0.0")
            current["assets"][0]["digest"] = "sha256:" + checksum
            self.assertEqual(u.checksum_for_release(url, "example/sample", "v1.0.0"), checksum)
            current["assets"][0]["digest"] = "sha256:wrong"
            with self.assertRaises(ValueError):
                u.checksum_for_release(url, "example/sample", "v1.0.0")
            for invalid in ({"draft": True}, {"prerelease": True}, {"tag_name": "wrong"}, {"assets": []}, {"assets": release["assets"] * 2}):
                current = dict(release, **invalid)
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    u.checksum_for_release(url, "example/sample", "v1.0.0")
        current = copy.deepcopy(release)
        def failed_download(*args):
            if args[0] == "gh":
                return json.dumps(current)
            raise subprocess.CalledProcessError(22, "curl")
        with patch.object(u, "run", side_effect=failed_download), self.assertRaises(subprocess.CalledProcessError):
            u.checksum_for_release(url, "example/sample", "v1.0.0")
        with patch.object(u, "run", side_effect=subprocess.CalledProcessError(1, "gh")), self.assertRaises(subprocess.CalledProcessError):
            u.checksum_for_release(url, "example/sample", "v1.0.0")

    def test_readme_stable_escaped_preserves_prose(self):
        sample = info()
        sample.update(name=["A [name] | `x`"], desc="Line\none | two <b>", homepage="https://example.com/a(b)")
        result = u.readme_tables(README, {"sample": sample, "aaa": info("aaa")})
        self.assertEqual(result, u.readme_tables(result, {"sample": sample, "aaa": info("aaa")}))
        self.assertTrue(result.startswith("Before\n"))
        self.assertTrue(result.endswith("\nAfter\n"))
        self.assertIn("\nMiddle\n", result)
        self.assertIn(r"A \[name\] \| \`x\`", result)
        self.assertIn("a%28b%29", result)
        self.assertLess(result.index(f"{u.TAP}/aaa"), result.index(f"{u.TAP}/sample"))
        with self.assertRaises(ValueError):
            u.readme_tables("No markers", {"sample": sample})

    def test_all_current_and_fourth_cask(self):
        original_files = {}
        for token in ("axolotl-launcher", "example-one", "example-two", "sample"):
            path = self.root / f"Casks/{token}.rb"
            path.write_text(SOURCE.replace('cask "sample"', f'cask "{token}"'))
            original_files[path] = path.read_text()
        with patch.object(u, "metadata", side_effect=lambda token: info(token)), patch.object(u, "latest_version", return_value=None):
            u.update(self.root)
            first = (self.root / "README.md").read_text()
            u.update(self.root)
            self.assertEqual(first, (self.root / "README.md").read_text())
        for path, text in original_files.items():
            self.assertEqual(text, path.read_text())
            self.assertIn(f"{u.TAP}/{path.stem}", first)

    def test_failure_leaves_entire_proposal_unchanged(self):
        second = self.root / "Casks/second.rb"
        second.write_text(SOURCE)
        with patch.object(u, "metadata", side_effect=lambda token: info(token)), patch.object(u, "candidate", side_effect=[SOURCE.replace("1.0.0", "1.1.0"), RuntimeError("network")]):
            with self.assertRaises(RuntimeError):
                u.update(self.root)
        self.assertEqual(SOURCE, self.path.read_text())
        self.assertEqual(SOURCE, second.read_text())
        self.assertEqual(README, (self.root / "README.md").read_text())

    def test_unsupported_skipped_and_readme_only(self):
        with patch.object(u, "metadata", return_value=info()), patch.object(u, "candidate", side_effect=u.Unsupported("complex")), patch("builtins.print"):
            u.update(self.root)
        self.assertEqual(SOURCE, self.path.read_text())
        with patch.object(u, "metadata", return_value=info()), patch.object(u, "candidate") as candidate:
            u.update(self.root, readme_only=True)
            candidate.assert_not_called()

    def test_manifest_rejects_changed_added_deleted_files_and_modes(self):
        manifest = self.root / "manifest.json"
        names = "Casks/sample.rb\x00README.md\x00"
        def fake_git(*args):
            if "ls-files" in args:
                return names
            if "rev-parse" in args:
                return "base\n"
            return "README.md\x00"
        with patch.object(u, "run", side_effect=fake_git):
            manifest.write_text(json.dumps(u.snapshot(self.root)))
            u.verify(self.root, manifest.parent)
            self.path.write_text(SOURCE + "# injected\n")
            with self.assertRaises(ValueError):
                u.verify(self.root, manifest.parent)
            self.path.write_text(SOURCE)
            self.path.chmod(0o755)
            with self.assertRaises(ValueError):
                u.verify(self.root, manifest.parent)
            self.path.chmod(0o644)
            names += "injected.rb\x00"
            (self.root / "injected.rb").write_text("injected")
            with self.assertRaises(ValueError):
                u.verify(self.root, manifest.parent)
            names = "README.md\x00"
            with self.assertRaises(ValueError):
                u.verify(self.root, manifest.parent)
            names = "Casks/sample.rb\x00README.md\x00"
            expected = json.loads(manifest.read_text())
            expected["changes"] = ["Casks/sample.rb"]
            manifest.write_text(json.dumps(expected))
            with self.assertRaises(ValueError):
                u.verify(self.root, manifest.parent)


if __name__ == "__main__":
    unittest.main()
