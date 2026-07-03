"""Draft demo — 迁自 example.py（阶段5 拆分）。"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER, LICENSE_KEY
from text_demo import add_subtitle_impl


def save_draft_impl(draft_id, draft_folder):
    """API wrapper for save_draft service"""
    data = {
        "license_key": LICENSE_KEY,  # Using trial version license key
        "draft_id": draft_id,
        "draft_folder": draft_folder
    }
    return make_request("save_draft", data)

def query_script_impl(draft_id):
    """API wrapper for query_script service"""
    data = {
        "draft_id": draft_id
    }
    return make_request("query_script", data)

def query_draft_status_impl(task_id):
    """API wrapper for query_draft_status service"""
    data = {
        "license_key": LICENSE_KEY,  # Using trial version license key
        "task_id": task_id
    }
    return make_request("query_draft_status", data)

def query_draft_status_impl_polling(task_id, timeout=300, callback=None):
    """
    Poll for draft download status, implemented with async thread to avoid blocking the main thread

    :param task_id: task ID returned by save_draft_impl
    :param timeout: timeout in seconds, default 5 minutes
    :param callback: optional callback function called when task completes, fails or times out, with final status as parameter
    :return: tuple of thread object and result container, can be used to get results later
    """
    # Create result container to store final result
    result_container = {"result": None}

    def _polling_thread():
        start_time = time.time()
        print(f"Starting to query status for task {task_id}...")

        while True:
            try:
                # Get current task status
                task_status = query_draft_status_impl(task_id).get("output", {})

                # Print current status
                status = task_status.get("status", "unknown")
                message = task_status.get("message", "")
                progress = task_status.get("progress", 0)
                print(f"Current status: {status}, progress: {progress}%, message: {message}")

                # Check if completed or failed
                if status == "completed":
                    print(f"Task completed! Draft URL: {task_status.get('draft_url', 'Not provided')}")
                    result_container["result"] = task_status.get('draft_url', 'Not provided')
                    if callback:
                        callback(task_status.get('draft_url', 'Not provided'))
                    break
                elif status == "failed":
                    print(f"Task failed: {message}")
                    result_container["result"] = task_status
                    if callback:
                        callback(task_status)
                    break
                elif status == "not_found":
                    print(f"Task does not exist: {task_id}")
                    result_container["result"] = task_status
                    if callback:
                        callback(task_status)
                    break

                # Check if timed out
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    print(f"Query timed out, waited {timeout} seconds")
                    result_container["result"] = task_status
                    if callback:
                        callback(task_status)
                    break
            except Exception as e:
                # Catch all exceptions to prevent thread crash
                print(f"Exception occurred during query: {e}")
                time.sleep(1)  # Wait 1 second before retrying after error
                continue

            # Wait 1 second before querying again
            time.sleep(1)

    # Create and start thread
    thread = threading.Thread(target=_polling_thread)
    # thread.daemon = True  # Set as daemon thread, automatically terminates when main thread ends
    thread.start()

    # Return thread object and result container for external code to get results
    return thread, result_container
