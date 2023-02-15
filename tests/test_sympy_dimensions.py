from sympy.core.numbers import One
from sympy.physics.units.definitions.dimension_definitions import angle
from sympy.physics.units import length, time, mass, temperature, current
from mira.sources.space_latex import parse_sympy_units, dimension_mapping


def test_dimensionless():
    unit = "-"
    parsed = parse_sympy_units(unit)
    assert parsed == dimension_mapping['-']
    assert parsed == One()


def test_base_units():
    # Length, meters
    length_unit = "m"
    parsed = parse_sympy_units(length_unit)
    assert parsed == dimension_mapping[length_unit]
    assert parsed == length

    # Time, seconds
    time_unit = "s"
    parsed = parse_sympy_units(time_unit)
    assert parsed == dimension_mapping[time_unit]
    assert parsed == time

    # Mass, kilograms
    mass_unit = "kg"
    parsed = parse_sympy_units(mass_unit)
    assert parsed == dimension_mapping[mass_unit]
    assert parsed == mass

    # Temperature, kelvin/K
    temperature_unit = "K"
    parsed = parse_sympy_units(temperature_unit)
    assert parsed == dimension_mapping[temperature_unit]
    assert parsed == temperature

    # Current, ampere/A
    current_unit = "A"
    parsed = parse_sympy_units(current_unit)
    assert parsed == dimension_mapping[current_unit]
    assert parsed == current


def test_angles():
    # Angle, degrees
    angle_unit = "deg"
    parsed = parse_sympy_units(angle_unit)
    assert parsed == dimension_mapping[angle_unit]
    assert parsed == angle

    # Angle, radians
    angle_unit = "rad"
    parsed = parse_sympy_units(angle_unit)
    assert parsed == dimension_mapping[angle_unit]
    assert parsed == angle


def test_joules():
    joule_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2}"
    parsed = parse_sympy_units(joule_unit)
    joules = mass * length ** 2 * time ** -2
    assert parsed == joules


def test_newtons():
    # Newton = mass * acceleration = mass * length * time ** -2
    newton_unit = r"\mathrm{kg} \cdot \mathrm{m} \cdot \mathrm{s}^{-2}"
    parsed = parse_sympy_units(newton_unit)
    newtons = mass * length * time ** -2
    assert parsed == newtons


def test_watts():
    # Watt = power = energy / time = mass * length ** 2 * time ** -3
    watt_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-3}"
    parsed = parse_sympy_units(watt_unit)
    watts = mass * length ** 2 * time ** -3
    assert parsed == watts


def test_tesla():
    # Tesla = magnetic flux density = magnetic flux / area = mass * length ** 2 * time ** -2 * current ** -1
    tesla_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2} \cdot \mathrm{A}^{-1}"
    parsed = parse_sympy_units(tesla_unit)
    tesla = mass * length ** 2 * time ** -2 * current ** -1
    assert parsed == tesla


def test_boltzmann_constant():
    # k_B = Boltzmann constant = 1.380649e-23 J/K
    # J/K = kg * m ** 2 * s ** -2 * K ** -1
    boltzmann_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2} \cdot \mathrm{K}^{-1}"
    parsed = parse_sympy_units(boltzmann_unit)
    boltzmann = mass * length ** 2 * time ** -2 * temperature ** -1
    assert parsed == boltzmann
