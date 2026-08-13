from fizzbuzz import fizzbuzz


def test_basic():
    assert fizzbuzz(1) == ["1"]
    assert fizzbuzz(3) == ["1", "2", "Fizz"]
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]


def test_fizzbuzz_on_multiples_of_15():
    result = fizzbuzz(15)
    assert result[14] == "FizzBuzz"


def test_length():
    assert len(fizzbuzz(20)) == 20
