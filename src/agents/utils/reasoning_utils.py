import requests
from time import sleep

# Visualize PPI
def generate_string_network_image(proteins, output_file=None):
    species = 9606
    format = "image"

    hide_disconnected_nodes = 0
    net_type = "functional"

    net_flavor = "evidence"
    output_filename = None

    caller = "my_python_script"

    string_api_url = "https://string-db.org/api"
    method = "network"
    request_url = "/".join([string_api_url, format, method])

    identifiers_string = "%0d".join(proteins)

    params = {
        "identifiers": identifiers_string,
        "species": species,
        "network_type": net_type,
        "network_flavor": net_flavor,
        "hide_disconnected_nodes": hide_disconnected_nodes,
        "caller_identity": caller
    }

    try:
        response = requests.post(request_url, data=params)
        response.raise_for_status()
        if output_file is None:
            base_filename = "_".join(proteins[:3])
            if len(proteins) > 3:
                base_filename += "_etc"
            file_extension = "png" if "image" in format else format
            output_file = f"{base_filename}_species_{species}_network.{file_extension}"

        with open(output_file, 'wb') as fh:
            fh.write(response.content)

        sleep(1)

        return output_file

    except requests.exceptions.RequestException as e:
        print(f"\nError during STRING API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            pass
        return None
    except IOError as e:
        print(f"\nError writing file {output_file}: {e}")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return None
    
def generate_string_network_image_and_link_to_webpage(proteins, output_file=None):
    image_path = generate_string_network_image(proteins, output_file)
    if not image_path:
        return None, None
    string_api_url = "https://string-db.org/api"
    method = "get_link"
    format = "json" 
    request_url = "/".join([string_api_url, format, method])

    identifiers_string = "%0d".join(proteins)
    params = {
        "identifiers": identifiers_string,
        "species": 9606,  
        "network_flavor": "evidence",
        "network_type": "functional",
        "hide_disconnected_nodes": 0,
        "required_score": 400,
        "caller_identity": "my_python_script"
    }

    try:
        response = requests.get(request_url, params=params)
        response.raise_for_status()
        web_url = response.json()[0]
        return image_path, web_url
    except requests.exceptions.RequestException as e:
        # print(f"\nError getting STRING webpage URL: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}...")
        return image_path, None
    except Exception as e:
        print(f"\nAn unexpected error occurred while getting webpage URL: {e}")
        return image_path, None
    
def pathway_overview_tbl(df):
    temp = df[["native", "name", "intersection_size", "score", "p_value", "source"]]
    temp["p_value"] = temp["p_value"].apply(lambda x: f"{x:.3e}")
    temp["score"] = temp["score"].apply(lambda x: f"{x:.3f}")
    temp.rename(columns={"native": "Term ID", "name": "Pathway Name", "p_value": "p-value", "intersection_size": "Associated Proteins Counts", "score": "Weighted Score", "source": "Source"}, inplace=True)
    
    header = "| " + " | ".join(temp.columns.astype(str)) + " |"
    separator = "| " + " | ".join(["---"] * len(temp.columns)) + " |"
    
    rows = temp.astype(str).apply(lambda row: "| " + " | ".join(row) + " |", axis=1)
    
    markdown_table = "\n".join([header, separator] + rows.tolist())
    return markdown_table