def get_request_queue(
    filename: str,
    request_obj: dict[tuple[str, int], dict[str, list[str]]],
    curr_pieces_info: dict[str, list[str]],
) -> dict[tuple[str, int], list[str]]:
    def create_request_queue(filename: str, data: dict[int, list[str]]):

        # return key whose value has the minimum length
        def get_min_key(d, keys):
            # Initialize min_key as None and min_length as infinity to find the minimum
            min_key = None
            min_length = float("inf")

            for key in keys:
                list_length = len(d[key])
                if list_length < min_length:
                    min_length = list_length
                    min_key = key
            return min_key

        # Get the request queue
        result = {key: [] for key in data}
        keys = list(data.keys())
        total_value = 0
        for value in data.values():
            total_value += len(value)
        while total_value > 0:
            listkey = keys.copy()

            # Loop through remaining keys(node's port) to update correspond request queue
            while len(listkey) > 0:
                min_key = get_min_key(data, listkey)

                # Remove key whose value is an empty list
                if len(data[min_key]) == 0:
                    keys.remove(min_key)
                    listkey.remove(min_key)
                    continue

                # Append request queue of corresponding node
                piece = data[min_key][0]
                piece_name = f"{filename}_{piece}.txt"
                result[min_key].append(piece_name)

                # remove ${piece} in each of keys'value (if any) and decrease total_value
                for eachkey in keys:
                    if piece in data[eachkey]:
                        data[eachkey].remove(piece)
                        total_value -= 1
                listkey.remove(min_key)
        return result

    # Initialize dictionary in which keys are nodes address
    # and assign value with the list of pieces derived from ${filename} each nodes possesses
    data = {key: [] for key in request_obj}
    for key in list(request_obj.keys()):
        value = request_obj[key]
        if not value.get(filename):
            del data[key]
            continue
        data[key] = value[filename]

    # remove pieces in nodes that client already possesses (if any)
    if curr_pieces_info.get(filename):
        for key in list(data.keys()):
            duplicate_piece = curr_pieces_info.get(filename)
            for value in duplicate_piece:
                if value in data[key]:
                    data[key].remove(value)

    # get request_queue for each node
    request_queue = {key: [] for key in data}
    file_name = filename.split(".")[0]
    request_queue = create_request_queue(file_name, data)
    return request_queue


request_obj = {
    ("127.0.0.1", 55157): {"3.txt": ["0", "1", "2", "3"], "4.txt": ["2", "3"]},
    ("127.0.0.1", 55170): {"3.txt": ["0", "2", "4"]},
}
curr_pieces_info = {"2.txt": ["2"], "3.txt": ["1", "2"]}


result_data2 = get_request_queue("5.txt", request_obj, curr_pieces_info)
print("Returned dictionary:", result_data2)
