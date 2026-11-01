from pathlib import Path

from scripts.build_evidence import capture_snapshot, compare_snapshots


def test_changed_source_and_rebuilt_artifact_do_not_identify_runtime(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Source.java"
    artifact = tmp_path / "app.jar"
    source.write_text("old")
    artifact.write_bytes(b"old jar")
    old = capture_snapshot(
        tmp_path, [Path("Source.java")], Path("app.jar"), build_exit_code=0
    )
    source.write_text("new")
    unbuilt = capture_snapshot(tmp_path, [Path("Source.java")], Path("app.jar"))
    assert compare_snapshots(old, unbuilt) == {
        "sourceChanged": True,
        "localArtifactChanged": False,
        "runtimeIdentityComparison": "unknown",
    }
    artifact.write_bytes(b"new jar")
    rebuilt = capture_snapshot(
        tmp_path, [Path("Source.java")], Path("app.jar"), build_exit_code=0
    )
    assert compare_snapshots(old, rebuilt) == {
        "sourceChanged": True,
        "localArtifactChanged": True,
        "runtimeIdentityComparison": "unknown",
    }
    assert rebuilt["runtimeIdentity"] == {"state": "notCollected", "sha256": None}
    assert rebuilt["build"]["artifactProducedByBuild"] == "unknown"


def test_missing_and_symlinks_are_unknown(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("never read")
    project = tmp_path / "project"
    project.mkdir()
    (project / "link").symlink_to(outside, target_is_directory=True)
    (project / "filelink").symlink_to(outside / "secret")
    for path in (
        Path("missing"),
        Path("../outside/secret"),
        Path("link/secret"),
        Path("filelink"),
    ):
        snapshot = capture_snapshot(project, [path], path)
        assert snapshot["source"]["sha256"] is None
        assert snapshot["localArtifact"]["sha256"] is None
        assert compare_snapshots(snapshot, snapshot)["sourceChanged"] is None


def test_failed_build_does_not_certify_existing_artifact(tmp_path: Path) -> None:
    (tmp_path / "source").write_text("broken")
    (tmp_path / "artifact").write_bytes(b"old artifact")
    snapshot = capture_snapshot(
        tmp_path, [Path("source")], Path("artifact"), build_exit_code=1
    )
    assert snapshot["localArtifact"]["sha256"] is not None
    assert snapshot["build"]["outcome"] == "failed"
    assert snapshot["build"]["artifactProducedByBuild"] == "unknown"
