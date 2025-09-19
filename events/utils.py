def format_card_data(data):
    parts = data.split("=")
    if len(parts) < 2:
        return None
    student_id = parts[0]
    student_id = student_id.replace(";", "")
    print(student_id)
    return student_id


def is_valid_card_data(data):
    # Implement your validation logic here
    # For example, check if the data is a number and has the correct length
    return data.isdigit() and len(data) == 16


def is_valid_net_id(data):
    letters = data[0:3]
    numbers = data[3:]
    is_correct_length = len(letters) == 3 and len(numbers) == 6
    return is_correct_length and letters.isalpha() and numbers.isdigit()
