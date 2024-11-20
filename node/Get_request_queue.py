def get_request_queue_optimize(
    file_name: str, request_obj: dict[(str, int), dict[str, list[str]]]
) -> dict[(str, int), dict[str, list[str]]]:
    def get_min_key(d, keys):

        min_key = None
        min_length = float("inf")

        for key in keys:
            list_length = len(d[key])
            if list_length < min_length:
                min_length = list_length
                min_key = key
        return min_key

    data = {key: [int(item) for item in value] for key, value in data.items()}
    result = {key: [] for key in data}
    keys = list(data.keys())
    total_value = 0
    for value in data.values():
        total_value += len(value)  # Tính số phần tử trong mỗi list (value)
    while total_value > 0:
        listkey = keys.copy()
        while len(listkey) > 0:
            min_key = get_min_key(data, listkey)
            if len(data[min_key]) == 0:
                keys.remove(min_key)
                listkey.remove(min_key)
                continue
            value = data[min_key][0]
            piece_name = f"{value}"
            result[min_key].append(piece_name)
            for eachkey in keys:
                if value in data[eachkey]:
                    data[eachkey].remove(value)
                    total_value -= 1
            listkey.remove(min_key)
    return result


# Ví dụ sử dụng
sample_data2 = {
    ("127.0.0.1", 8001): ["1", "2", "4", "5"],
    ("127.0.0.1", 8002): ["2", "5", "7"],
    ("127.0.0.1", 8003): ["2"],
    ("127.0.0.1", 8004): ["1", "2", "5", "6", "7"],
}

result_data2 = get_request_queue_optimize(sample_data2)
print("Returned dictionary:", result_data2)
