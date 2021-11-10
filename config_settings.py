import configparser
from flask import jsonify
def get_value(key_string):

    config = configparser.ConfigParser()

    try:
        num_of_files_loaded = config.read('../lca_config.ini', encoding='utf8')
        if len(num_of_files_loaded) != 1:
            error_text = '"Contact server host. Error is "configuration file not found"'
            print(error_text)
            return None, error_text
        else:
            value = config.get(*key_string)
            return value, ""
    except FileNotFoundError as e:
        error_text = 'File not found'
        print(error_text)
        return None, error_text
    except KeyError as e:
        error_text = f"get value({key_string})"
        print("KeyError(config)",error_text)
        return None
    except Exception as e:
        error_text = f"get value({key_string})"
        print("Exception(config)",error_text)
        return None


def get_full_access_settings():

    config_server_security_key, config_messsage_text = get_value(['http_config','fullaccess'])

    if config_server_security_key is None:
        data_show = {"notification": {"text": config_messsage_text},
                     "heading": "Authorization error",
                     "prompt_options": "",
                     "setting":
                         {"duration": 10000}
                     }
        return None, jsonify(data_show)
    elif config_server_security_key == "false":
        return False, None
    elif config_server_security_key == "true":
        return True, None
    else:
        data_show = {"notification": {"text": f"Invalid value ({config_server_security_key}) is set"},
                     "heading": "Authorization error",
                     "prompt_options": "",
                     "setting":
                         {"duration": 10000}
                     }
        return None, jsonify(data_show)


if __name__ == "__main__":

    return_value = get_value(['connection.config.dictionary','merriam_api'])
    print(return_value)

