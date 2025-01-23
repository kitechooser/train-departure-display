import requests

# TfL API credentials (replace these with your actual credentials)
API_ID = "DepartureBoard"
API_KEY = "a432a817f61d4a65ba62e226e48e665b"

# TfL API endpoint for line statuses
BASE_URL = "https://api.tfl.gov.uk"

def get_detailed_line_status(line_name):
    """
    Fetches detailed service status for a specific line from the TfL API.

    Args:
        line_name (str): The name of the line (e.g., 'central', 'northern').

    Returns:
        str: Detailed service status of the line or an error message.
    """
    try:
        # Make a request to the TfL API
        url = f"{BASE_URL}/Line/{line_name}/Status?app_id={API_ID}&app_key={API_KEY}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        data = response.json()

        # Extract and return the service status
        if data:
            line = data[0]
            name = line.get("name", "Unknown Line")
            statuses = line.get("lineStatuses", [])
            
            # Build detailed status information
            detailed_status = [f"- {status['statusSeverityDescription']}: {status.get('reason', 'No additional information.')}" for status in statuses]
            
            # Return the line name and detailed status with extra space for scrolling
            status_text = f"{name} Line Status:\n" + "\n".join(detailed_status)
            # No padding needed - text is long enough
            return status_text
        else:
            return f"No status found for line: {line_name}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching line status: {e}"
    except KeyError:
        return "Unexpected response format from TfL API."

# Test the function with a sample line name
if __name__ == "__main__":
    line_name = input("Enter the line name (e.g., 'central', 'northern'): ").strip().lower()
    status = get_detailed_line_status(line_name)
    print(status)
