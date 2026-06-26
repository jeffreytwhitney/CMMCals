from datetime import datetime, timedelta
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def get_recent_files(directory_path, hours=48):
    """
    Enumerate files in the specified directory and return those created in the past specified hours.

    Args:
        directory_path: Path to the directory to scan
        hours: Number of hours to look back (default: 48)

    Returns:
        List of file paths that were created within the specified timeframe
    """
    # Calculate the cutoff time
    cutoff_time = datetime.now() - timedelta(hours=hours)

    # Convert to Path object
    dir_path = Path(directory_path)

    # Check if directory exists
    if not dir_path.exists():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return []

    if not dir_path.is_dir():
        print(f"Error: '{directory_path}' is not a directory.")
        return []

    recent_files = []

    # Enumerate all files in the directory
    try:
        for item in dir_path.iterdir():
            if item.is_file():
                # Get modification time
                modification_time = datetime.fromtimestamp(item.stat().st_mtime)

                # Check if file was modified within the past 48 hours
                if modification_time >= cutoff_time:
                    recent_files.append(item)
    except PermissionError as e:
        print(f"Error: Permission denied while accessing '{directory_path}': {e}")
        return []
    except Exception as e:
        print(f"Error while scanning directory: {e}")
        return []

    return recent_files

def get_latest_report_times_by_machine(directory_path, machine_name_length=5):
    """
    Enumerate files in the specified directory and return the latest report time for each machine.

    Args:
        directory_path: Path to the directory to scan
        machine_name_length: Length of the machine prefix in file names (default: 5)

    Returns:
        Dict keyed by machine name with latest report datetime values
    """
    dir_path = Path(directory_path)

    if not dir_path.exists():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return {}

    if not dir_path.is_dir():
        print(f"Error: '{directory_path}' is not a directory.")
        return {}

    latest_report_times = {}

    try:
        for item in dir_path.iterdir():
            if not item.is_file():
                continue

            file_name = item.name.strip()
            if len(file_name) < machine_name_length:
                continue

            machine_name = file_name[:machine_name_length]
            mod_time = datetime.fromtimestamp(item.stat().st_mtime)
            current_latest = latest_report_times.get(machine_name)

            if current_latest is None or mod_time > current_latest:
                latest_report_times[machine_name] = mod_time
    except PermissionError as e:
        print(f"Error: Permission denied while accessing '{directory_path}': {e}")
        return {}
    except Exception as e:
        print(f"Error while scanning directory: {e}")
        return {}

    return latest_report_times


def get_machine_descriptions_from_xml(xml_path):
    """
    Parse the CMMs.xml file and return a lookup of machine name -> description.

    Args:
        xml_path: Path to the CMMs.xml file

    Returns:
        Dict keyed by machine name with description values
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        machine_descriptions = {}
        for cmm in root.findall('CMM'):
            machine_name_element = cmm.find('MachineName')
            description_element = cmm.find('Description')

            if machine_name_element is None or not machine_name_element.text:
                continue

            machine_name = machine_name_element.text.strip()
            description = description_element.text.strip() if description_element is not None and description_element.text else ""
            machine_descriptions[machine_name] = description

        return machine_descriptions
    except FileNotFoundError:
        print(f"Error: XML file '{xml_path}' not found.")
        return {}
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return {}
    except Exception as e:
        print(f"Error reading XML file: {e}")
        return {}


def get_machine_names_from_xml(xml_path):
    """
    Parse the CMMs.xml file and extract all machine names.

    Args:
        xml_path: Path to the CMMs.xml file

    Returns:
        Set of machine names from the XML file
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        machine_names = set()
        for cmm in root.findall('CMM'):
            machine_name_element = cmm.find('MachineName')
            if machine_name_element is not None and machine_name_element.text:
                machine_names.add(machine_name_element.text.strip())

        return machine_names
    except FileNotFoundError:
        print(f"Error: XML file '{xml_path}' not found.")
        return set()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return set()
    except Exception as e:
        print(f"Error reading XML file: {e}")
        return set()


def main():
    # Directory to scan
    cal_results_dir = r"V:\Inspect Programs\Metrology Printouts\cal results"

    # Path to CMMs.xml file (in the same directory as this script)
    script_dir = Path(__file__).parent
    cmms_xml_path = r"X:\Quality Calibration\CMMs.xml"
    current_date = datetime.today().strftime('%m/%d/%Y')

    print(f"Reading machine names from: {cmms_xml_path}")
    print(f"Scanning directory: {cal_results_dir}")
    print(f"Looking for machines that have NOT run in the past 48 hours...")
    print("-" * 80)

    # Get all machine descriptions from the XML file
    machine_descriptions = get_machine_descriptions_from_xml(cmms_xml_path)
    machine_names = set(machine_descriptions.keys())

    if not machine_names:
        print("No machine names found in XML file or error occurred.")
        return

    print(f"Found {len(machine_names)} machines in CMMs.xml")

    # Get each machine's latest report date from all available files.
    latest_report_times = get_latest_report_times_by_machine(cal_results_dir)

    # Get files from the past 48 hours
    recent_files = get_recent_files(cal_results_dir, hours=48)

    print(f"Found {len(recent_files)} files modified in the past 48 hours")

    # Extract machine names from the file names (first 5 characters)
    machines_with_recent_files = set()
    for file_path in recent_files:
        file_name = file_path.name.strip()
        if len(file_name) >= 5:
            machines_with_recent_files.add(file_name[0:5])

    print(f"Found {len(machines_with_recent_files)} machines with recent cal results")
    print("-" * 80)

    # Find machines that are in XML but have NOT run in the past 48 hours
    machines_not_run = sorted(machine_names - machines_with_recent_files)

    if machines_not_run:
        print(f"{current_date}: Machines that have NOT calibrated in the past 48 hours ({len(machines_not_run)}):\n")
        print(f"{'Machine':<8} {'Days Since Cal':<15} Description")
        print("-" * 80)

        now = datetime.now()
        for machine_name in machines_not_run:
            description = machine_descriptions.get(machine_name, "")
            last_report_time = latest_report_times.get(machine_name)
            days_since_cal = (now - last_report_time).days if last_report_time else None
            days_since_text = str(days_since_cal) if days_since_cal is not None else "Never"
            print(f"{machine_name:<8} {days_since_text:<15} {description}")
    else:
        print(f"{current_date}: All machines have calibrated in the past 48 hours!")

    print("-" * 80)
    print("Scan complete.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # Keep console open for interactive runs (e.g., double-click execution).
        if sys.stdin.isatty():
            input("\nPress Enter to close...")
