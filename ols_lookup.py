import requests
import json
import argparse

def calculate_overlap(str1, str2):
    """
    Calculate the overlap between two strings.

    Parameters:
    str1 (str): The first string.
    str2 (str): The second string.

    Returns:
    float: The overlap between the two strings.
    """
    str1, str2 = str1.lower(), str2.lower()
    overlap = sum(1 for a, b in zip(str1, str2) if a == b)
    return overlap / len(str1)

def fetch_searchStr_info(searchStr, type='class,individual', ontology_name=None):
    """
    Fetch searchStr information from the EBI OLS4 API.

    Parameters:
    searchStr (str): The search string.
    type (str): The type of search. Default is 'class,individual'.
    ontology_name (str): The name of the ontology. Default is None.

    Returns:
    dict: The JSON response from the API.
    """
    base_url = "https://www.ebi.ac.uk/ols4/api/search"
    params = {
        'q': searchStr,
        'type': type,
        'fieldList': 'iri,label,short_form,obo_id,ontology_name',
        'queryFields': 'iri,label,short_form,ontology_name',
        'exact': 'false',
        'groupField': 'http://www.ebi.ac.uk/efo/EFO_0001421',
        'obsoletes': 'false',
        'local': 'false',
        'rows': '10',
        'start': '0',
        'format': 'json',
        'lang': 'en'
    }

    if ontology_name:
        params['ontology'] = ontology_name

    headers = {
        'accept': '*/*'
    }

    response = requests.get(base_url, params=params, headers=headers)
    return response.json()

def generate_substrings(input_string):
    """
    Generate all possible substrings from a given string.

    Parameters:
    input_string (str): The input string.

    Returns:
    list: A list of substrings.
    """
    words = input_string.split()
    substrings = []

    # All possible substrings
    for i in range(len(words)):
        for j in range(i+1, len(words)+1):
            substrings.append(' '.join(words[i:j]))

    # All individual words
    substrings.extend(words)

    # Sort the list by length of the items
    substrings.sort(key=len, reverse=True)

    return substrings

def get_matching_entries(searchStr, type=None, ontology_name=None):
    """
    Get matching entries for a given searchStr.

    Parameters:
    searchStr (str): The search string.
    type (str): The type of search. Default is None.
    ontology_name (str): The name of the ontology. Default is None.

    Returns:
    tuple: A tuple containing a list of labels and a list of entries.
    """
    searchStr_parts = generate_substrings(searchStr)
    entries = []
    labels = []
    for part in searchStr_parts:
        data = fetch_searchStr_info(part, type=type, ontology_name=ontology_name)
        for doc in data['response']['docs']:
            labels.append(doc['label'])
            entries.append(doc)

    return labels, entries

def find_best_match(part, labels):
    """
    Find the best match for a given part in a list of labels.

    Parameters:
    part (str): The part to match.
    labels (list): A list of labels.

    Returns:
    str: The best match.
    """
    def word_overlap(part, label):
        part_words = set(part.lower().split())
        label_words = set(label.lower().split())
        overlap = part_words & label_words
        return len(overlap), len(label_words)

    best_match = None
    max_score = 0

    for label in labels:
        overlap, label_length = word_overlap(part, label)
        # Calculate a score that considers both overlap and label length
        score = overlap / label_length
        if score > max_score:
            max_score = score
            best_match = label

    return best_match

def read_json_file(file_path):
    """
    Read a JSON file and return the data.

    Parameters:
    file_path (str): The path to the JSON file.

    Returns:
    dict: The data from the JSON file.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def main(input_string, output_format, type=None, ontology_name=None):
    """
    Main function to handle the input and output.

    Parameters:
    input_string (str): The input string.
    output_format (str): The output format.
    type (str): The type of search. Default is None.
    ontology_name (str): The name of the ontology. Default is None.
    """
    labels, entries = get_matching_entries(input_string, type=type, ontology_name=ontology_name)
    best_match = find_best_match(input_string, labels)
    for i, label in enumerate(labels):
        if label == best_match:
            if output_format == 'iri':
                print(entries[i]['iri'])
            else:
                print(entries[i])
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch searchStr information.')
    parser.add_argument('input', type=str, help='Input string or JSON file path')
    parser.add_argument('--format', type=str, choices=['iri', 'json'], default='json', help='Output format')
    parser.add_argument('--type', type=str, help='Type of entity to search for (e.g. \'class,individual\')')
    parser.add_argument('--ontology', type=str, help='Name(s) of ontology(s) to search in (e.g. \'ncit,omit\')')
    args = parser.parse_args()

    if args.input.endswith('.json'):
        data = read_json_file(args.input)
        for key in data.keys():
            main(data[key], args.format, type=args.type, ontology_name=args.ontology)
    else:
        main(args.input, args.format, type=args.type, ontology_name=args.ontology)
