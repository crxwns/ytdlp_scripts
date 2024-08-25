from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yt_dlp  # pyright: ignore[reportMissingTypeStubs]

BASE_URL = "https://www.youtube.com/watch?v="
VIDEO_ID_PATTERN = re.compile(r"\[(.{11})\]")


def get_all_video_ids_from_channel(channelname: str) -> set[str]:
    """Retrieve all ID's from videos of that channel."""

    with yt_dlp.YoutubeDL({"extract_flat": "in_playlist", "ignoreerrors": "only_download"}) as ydl:
        info = ydl.extract_info(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            f"https://www.youtube.com/{channelname}/videos",
            download=False,
        )

    # Just here to check if returns are what we expect
    if not isinstance(info, dict):
        raise ValueError("Extract info didn't return a dict.")

    entries = info.get("entries")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not entries or not isinstance(entries, list):
        raise ValueError(f"No videos for channel: {channelname}")

    ids: list[str] = []

    for entry in entries:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(entry, dict):
            raise ValueError("Entry is not a dict.")

        ids.append(entry["id"])  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    return set(ids)


def get_all_video_ids_from_path(dirpath: Path) -> set[str]:
    """
    Retrieve all ID's from videos in a local path.
    Assumes that the ID is in the filename.
    """

    if not dirpath.is_dir():
        raise ValueError(f"Not a valid directory: {dirpath}")

    ids: list[str] = []

    for file in dirpath.glob("*"):
        match = VIDEO_ID_PATTERN.search(str(file))

        if not match:
            continue

        video_id = match.group(1)

        if video_id:
            ids.append(video_id)

    return set(ids)


def get_all_video_ids_not_locally_available(channelname: str, localpath: Path) -> set[str]:
    """Returns the diff of locally downloaded videos and available videos from the channel."""
    channel_ids = get_all_video_ids_from_channel(channelname=channelname)
    local_ids = get_all_video_ids_from_path(localpath)
    return channel_ids.difference(local_ids)


def download_missing_videos(
    channelname: str,
    localpath: Path,
    outpath: Path | None = None,
    dry_run: bool = False,
) -> None:
    """
    Downloads videos that haven't been downloaded locally.

    Args:
        channelname: Name of the channel e.g. @xyz

        localpath: Path to the directory of locally downloaded videos

        outpath: Defaults to localpath, downloads the videos to a different directory

        dry_run: Only outputs the URLs that would get downloaded
    """

    if not outpath:
        outpath = localpath

    urls = [
        BASE_URL + video_id
        for video_id in get_all_video_ids_not_locally_available(channelname=channelname, localpath=localpath)
    ]

    print(f"Downloading {len(urls)} missing videos")

    ydl_opts: dict[str, Any] = {
        "paths": {"home": str(outpath)},
        "postprocessors": [
            {
                "key": "FFmpegMetadata",
                "add_chapters": True,
                "add_metadata": True,
                "add_infojson": "if_exists",
            },
        ],
    }

    if dry_run:
        print(f"Would download: {urls}")
    else:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)  # pyright: ignore[reportUnknownMemberType]


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--channelname", required=True)
    parser.add_argument("-d", "--dirpath", type=Path, required=True)
    parser.add_argument("--dry", action="store_true")

    args = parser.parse_args()

    download_missing_videos(
        channelname=args.channelname,
        localpath=args.dirpath,
        dry_run=args.dry,
    )
