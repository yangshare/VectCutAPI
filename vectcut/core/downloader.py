"""媒体下载工具（迁自根 downloader.py，阶段5 任务2）。

函数实现逐字不变；仅模块位置移动。
"""
import os
import subprocess
import time
import requests
import shutil
from requests.exceptions import RequestException, Timeout

from vectcut.core.logger import sanitize_path, sanitize_text, sanitize_url


def _decode_stderr(stderr) -> str:
    if stderr is None:
        return ""
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace")
    return str(stderr)


def _ffmpeg_error(stderr) -> str:
    return sanitize_text(_decode_stderr(stderr))


def download_video(video_url, draft_name, material_name):
    """
    Download video to specified directory
    :param video_url: Video URL
    :param draft_name: Draft name
    :param material_name: Material name
    :return: Local video path
    """
    # Ensure directory exists
    video_dir = f"{draft_name}/assets/video"
    os.makedirs(video_dir, exist_ok=True)

    # Generate local filename
    local_path = f"{video_dir}/{material_name}"

    # Check if file already exists
    if os.path.exists(local_path):
        print(f"Video file already exists: {sanitize_path(local_path)}")
        return local_path

    try:
        # Use ffmpeg to download video
        command = [
            'ffmpeg',
            '-i', video_url,
            '-c', 'copy',  # Direct copy, no re-encoding
            local_path
        ]
        subprocess.run(command, check=True, capture_output=True)
        return local_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to download video: {_ffmpeg_error(e.stderr)}")


def download_image(image_url, draft_name, material_name):
    """
    Download image to specified directory, and convert to PNG format
    :param image_url: Image URL
    :param draft_name: Draft name
    :param material_name: Material name
    :return: Local image path
    """
    # Ensure directory exists
    image_dir = f"{draft_name}/assets/image"
    os.makedirs(image_dir, exist_ok=True)

    # Uniformly use png format
    local_path = f"{image_dir}/{material_name}"

    # Check if file already exists
    if os.path.exists(local_path):
        print(f"Image file already exists: {sanitize_path(local_path)}")
        return local_path

    try:
        # Use ffmpeg to download and convert image to PNG format
        command = [
            'ffmpeg',
            '-headers', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36\r\nReferer: https://www.163.com/\r\n',  # noqa: E501
            '-i', image_url,
            '-vf', 'format=rgba',  # Convert to RGBA format to support transparency
            '-frames:v', '1',      # Ensure only one frame is processed
            '-y',                  # Overwrite existing files
            local_path
        ]
        subprocess.run(command, check=True, capture_output=True)
        return local_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to download image: {_ffmpeg_error(e.stderr)}")


def download_audio(audio_url, draft_name, material_name):
    """
    Download audio and transcode to MP3 format to specified directory
    :param audio_url: Audio URL
    :param draft_name: Draft name
    :param material_name: Material name
    :return: Local audio path
    """
    # Ensure directory exists
    audio_dir = f"{draft_name}/assets/audio"
    os.makedirs(audio_dir, exist_ok=True)

    # Generate local filename (keep .mp3 extension)
    local_path = f"{audio_dir}/{material_name}"

    # Check if file already exists
    if os.path.exists(local_path):
        print(f"Audio file already exists: {sanitize_path(local_path)}")
        return local_path

    try:
        # Use ffmpeg to download and transcode to MP3 (key modification: specify MP3 encoder)
        command = [
            'ffmpeg',
            '-i', audio_url,          # Input URL
            '-c:a', 'libmp3lame',     # Force encode audio stream to MP3
            '-q:a', '2',              # Set audio quality (0-9, 0 is best, 2 balances quality and file size)
            '-y',                     # Overwrite existing files (optional)
            local_path                # Output path
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return local_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to download audio:\n{_ffmpeg_error(e.stderr)}")


def download_file(url: str, local_filename, max_retries=3, timeout=180):
    # 检查是否是本地文件路径
    if os.path.exists(url) and os.path.isfile(url):
        # 是本地文件，直接复制
        directory = os.path.dirname(local_filename)

        # 创建目标目录（如果不存在）
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {sanitize_path(directory)}")

        print(
            "Copying local file: "
            f"{sanitize_path(url)} to {sanitize_path(local_filename)}"
        )
        start_time = time.time()

        # 复制文件
        shutil.copy2(url, local_filename)

        print(f"Copy completed in {time.time()-start_time:.2f} seconds")
        print(f"File saved as: {sanitize_path(os.path.abspath(local_filename))}")
        return True

    # 原有的下载逻辑
    # Extract directory part
    directory = os.path.dirname(local_filename)

    retries = 0
    while retries < max_retries:
        try:
            if retries > 0:
                wait_time = 2 ** retries  # Exponential backoff strategy
                print(f"Retrying in {wait_time} seconds... (Attempt {retries+1}/{max_retries})")
                time.sleep(wait_time)

            print(f"Downloading file: {sanitize_path(local_filename)}")
            start_time = time.time()

            # Create directory (if it doesn't exist)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"Created directory: {sanitize_path(directory)}")

            # Add headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',  # noqa: E501
                'Referer': 'https://www.163.com/',  # 网易的Referer
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }

            with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024

                with open(local_filename, 'wb') as file:
                    bytes_written = 0
                    for chunk in response.iter_content(block_size):
                        if chunk:
                            file.write(chunk)
                            bytes_written += len(chunk)

                            if total_size > 0:
                                progress = bytes_written / total_size * 100
                                # 频繁更新进度时，建议用 logger.debug 或更细粒度控制，
                                # 避免日志文件过大；或仅输出到控制台，不写文件。
                                print(f"\r[PROGRESS] {progress:.2f}% ({bytes_written/1024:.2f}KB/{total_size/1024:.2f}KB)", end='')
                                pass  # Avoid printing too much progress information in log files

                if total_size > 0:
                    # print() # Original newline
                    pass
                print(f"Download completed in {time.time()-start_time:.2f} seconds")
                print(f"File saved as: {sanitize_path(os.path.abspath(local_filename))}")
                return True

        except Timeout:
            print(f"Download timed out after {timeout} seconds")
        except RequestException as e:
            print(f"Request failed: {type(e).__name__}")
        except Exception as e:
            print(f"Unexpected error during download: {type(e).__name__}")

        retries += 1

    print(f"Download failed after {max_retries} attempts for URL: {sanitize_text(url)}")
    return False
