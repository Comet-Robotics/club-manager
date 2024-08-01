def format_card_data(data):
        parts = data.split('+')
        if (len(parts) != 2):
            return None
        student_id = parts[1]
        student_id = student_id.replace('?', '')
        return student_id

def is_valid_card_data(data):
    # Implement your validation logic here
    # For example, check if the data is a number and has the correct length
    return data.isdigit() and len(data) == 10