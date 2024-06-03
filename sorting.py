import operator
from functools import reduce


def _split_sequence(sequence: list, *, fields: list[str]):
    sequence_without_none_field_values, sequence_with_none_field_values = [], []

    for obj in sequence:
        is_none_found = False

        for field_name in fields:
            field_value = getattr(obj, field_name)

            if field_value is None:
                is_none_found = True
                break

        if is_none_found:
            sequence_with_none_field_values.append(obj)
        else:
            sequence_without_none_field_values.append(obj)

    return sequence_without_none_field_values, sequence_with_none_field_values


def sort_collection_by_conditions(sequence: list, *conditions):
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


def sort_objects(sequence: list, *, fields: list[str], raise_if_field_not_found: bool = False):
    """
    Sort a collection of objects. Support field names and order marker

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
    all_fields = []

    for field_name in fields:
        reverse = field_name.startswith('-')

        if reverse:
            field_name = field_name[1:]

        is_field_found = hasattr(sequence[0], field_name)

        if is_field_found:
            attribute = operator.attrgetter(field_name)
            sort_conditions.append((attribute, reverse))
            all_fields.append(field_name)
        elif raise_if_field_not_found:
            sequence_elements_type = type(sequence[0])
            raise Exception(
                f'Field {field_name!r} not found for collection with elements of type {sequence_elements_type!r}'
            )

    sequence_without_none_field_values, sequence_with_none_field_values = (
        _split_sequence(sequence, fields=all_fields)
    )

    sorted_collection = sort_collection_by_conditions(
        sequence_without_none_field_values, *sort_conditions
    )

    sorted_collection.extend(sequence_with_none_field_values)
    return sorted_collection
