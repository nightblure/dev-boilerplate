def sort_collection_by_conditions(sequence, *conditions):
    """
    Sort a sequence by multiple criteria.

    Accepts a sequence and 0 or more (key, reverse) tuples, where
    the key is a callable used to extract the value to sort on
    from the input sequence, and reverse is a boolean dictating if
    this value is sorted in ascending or descending order.

    Sources:
    https://stackoverflow.com/questions/55866762/how-to-sort-a-list-of-strings-in-reverse-order-without-using-reverse-true-parame/55866810#55866810

    https://stackoverflow.com/questions/403421/how-do-i-sort-a-list-of-objects-based-on-an-attribute-of-the-objects
    """
    return reduce(
        lambda s, order: sorted(s, key=order[0], reverse=order[1]),
        reversed(conditions),
        sequence
    )


def sort_collection(sequence, *, fields: list[str], raise_if_field_not_found=False):
    """
    Support field names and order marker

    Example:
    ::
        collections = sort_collection(
            collection,
            fields=['name', '-created_at'],
            raise_if_field_not_found=True
        )
    """
    if not sequence:
        return sequence

    sort_conditions = []

    for field_name in fields:
        reverse = field_name.startswith('-')

        if reverse:
            field_name = field_name[1:]

        is_field_found = hasattr(sequence[0], field_name)

        if is_field_found:
            attribute = operator.attrgetter(field_name)
            sort_conditions.append((attribute, reverse))
        elif raise_if_field_not_found:
            sequence_elements_type = type(sequence[0])
            raise Exception(
                f'Field {field_name!r} not found for collection with elements of type {sequence_elements_type!r}'
            )

    return sort_collection_by_conditions(sequence, *sort_conditions)
  
