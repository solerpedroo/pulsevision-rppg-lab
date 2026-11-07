"""Stable errors for callers and the inspection CLI."""


class VideoError(Exception):
    code = "video_error"


class VideoOpenError(VideoError):
    code = "video_open_error"


class UnsupportedVideoError(VideoError):
    code = "unsupported_video"


class VideoDecodeError(VideoError):
    code = "video_decode_error"


class VideoTimestampError(VideoError):
    code = "invalid_timestamps"
