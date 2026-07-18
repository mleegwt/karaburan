#!/usr/bin/env python3
"""Generate deterministic ROS 2 MCAP data for the Foxglove measurement demo."""

import argparse
import gc
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import rosbag2_py
from karaburan_msgs.msg import ElectricalConductivity
from rclpy.serialization import serialize_message
from sensor_msgs.msg import NavSatFix, NavSatStatus, Range, Temperature
from std_msgs.msg import Float64


CENTER_LATITUDE_DEG = 52.0494
CENTER_LONGITUDE_DEG = 4.7521
ROUTE_RADIUS_METERS = 450.0
EARTH_RADIUS_METERS = 6_378_137.0
BASE_TEMPERATURE_C = 12.0
TEMPERATURE_AMPLITUDE_C = 10.0
GPS_INTERVAL_SECONDS = 1
TEMPERATURE_INTERVAL_SECONDS = 5
SONAR_INTERVAL_SECONDS = 1
BT785_INTERVAL_SECONDS = 10
ROUTE_DURATION_SECONDS = 360
START_TIME = datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc)


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).with_name(
        'reeuwijk-surfplas-temperature.mcap'
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output',
        type=Path,
        default=default_output,
        help=f'output MCAP file (default: {default_output})',
    )
    return parser.parse_args()


def coordinates_at_bearing(bearing_rad: float) -> tuple[float, float]:
    """Return a local small-circle approximation at a compass bearing."""
    latitude_offset = (
        ROUTE_RADIUS_METERS * math.cos(bearing_rad) / EARTH_RADIUS_METERS
    )
    longitude_offset = (
        ROUTE_RADIUS_METERS
        * math.sin(bearing_rad)
        / (EARTH_RADIUS_METERS * math.cos(math.radians(CENTER_LATITUDE_DEG)))
    )
    return (
        CENTER_LATITUDE_DEG + math.degrees(latitude_offset),
        CENTER_LONGITUDE_DEG + math.degrees(longitude_offset),
    )


def set_stamp(
    message: NavSatFix | Range | Temperature | ElectricalConductivity,
    timestamp_ns: int,
) -> None:
    message.header.stamp.sec = timestamp_ns // 1_000_000_000
    message.header.stamp.nanosec = timestamp_ns % 1_000_000_000


def add_topic(
    writer: rosbag2_py.SequentialWriter, topic_id: int, name: str, type_name: str
) -> None:
    writer.create_topic(
        rosbag2_py.TopicMetadata(
            id=topic_id,
            name=name,
            type=type_name,
            serialization_format='cdr',
        )
    )


def generate(output: Path) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    start_time_ns = int(START_TIME.timestamp() * 1_000_000_000)

    with tempfile.TemporaryDirectory(
        prefix='reeuwijk-surfplas-temperature-', dir=output.parent
    ) as temporary_directory:
        bag_directory = Path(temporary_directory) / 'rosbag2'
        writer = rosbag2_py.SequentialWriter()
        writer.open(
            rosbag2_py.StorageOptions(uri=str(bag_directory), storage_id='mcap'),
            rosbag2_py.ConverterOptions('', ''),
        )
        add_topic(writer, 0, '/fix/valid', 'sensor_msgs/msg/NavSatFix')
        add_topic(writer, 1, '/temperature', 'sensor_msgs/msg/Temperature')
        add_topic(
            writer,
            2,
            '/demo/bearing_from_center_deg',
            'std_msgs/msg/Float64',
        )
        add_topic(writer, 3, '/sonar', 'sensor_msgs/msg/Range')
        add_topic(
            writer,
            4,
            '/bt785',
            'karaburan_msgs/msg/ElectricalConductivity',
        )

        for elapsed_seconds in range(
            0, ROUTE_DURATION_SECONDS + 1, GPS_INTERVAL_SECONDS
        ):
            timestamp_ns = start_time_ns + elapsed_seconds * 1_000_000_000
            bearing_rad = 2 * math.pi * elapsed_seconds / ROUTE_DURATION_SECONDS
            bearing_deg = math.degrees(bearing_rad) % 360.0
            latitude, longitude = coordinates_at_bearing(bearing_rad)
            temperature_c = (
                BASE_TEMPERATURE_C
                + TEMPERATURE_AMPLITUDE_C * math.sin(bearing_rad)
            )
            sonar_depth_m = (
                8.0
                + 2.5 * math.cos(2 * bearing_rad)
                + 0.5 * math.sin(5 * bearing_rad)
            )
            conductivity_us_cm = 450.0 + 120.0 * math.sin(
                bearing_rad + math.pi / 4
            )
            probe_temperature_c = temperature_c + 0.35 * math.cos(
                2 * bearing_rad
            )

            if elapsed_seconds % TEMPERATURE_INTERVAL_SECONDS == 0:
                temperature = Temperature()
                set_stamp(temperature, timestamp_ns)
                temperature.header.frame_id = 'water_temperature_sensor'
                temperature.temperature = temperature_c
                temperature.variance = 0.0
                writer.write(
                    '/temperature', serialize_message(temperature), timestamp_ns
                )

            if elapsed_seconds % SONAR_INTERVAL_SECONDS == 0:
                sonar = Range()
                set_stamp(sonar, timestamp_ns)
                sonar.header.frame_id = 'sonar_link'
                sonar.radiation_type = Range.ULTRASOUND
                sonar.field_of_view = math.radians(45)
                sonar.min_range = 0.3
                sonar.max_range = 60.0
                sonar.range = sonar_depth_m
                writer.write('/sonar', serialize_message(sonar), timestamp_ns)

            if elapsed_seconds % BT785_INTERVAL_SECONDS == 0:
                bt785 = ElectricalConductivity()
                set_stamp(bt785, timestamp_ns)
                bt785.header.frame_id = 'bt785_link'
                bt785.conductivity = conductivity_us_cm
                bt785.temperature = probe_temperature_c
                writer.write('/bt785', serialize_message(bt785), timestamp_ns)

            bearing = Float64()
            bearing.data = bearing_deg
            writer.write(
                '/demo/bearing_from_center_deg',
                serialize_message(bearing),
                timestamp_ns,
            )

            fix = NavSatFix()
            set_stamp(fix, timestamp_ns)
            fix.header.frame_id = 'gps_link'
            fix.status.status = NavSatStatus.STATUS_FIX
            fix.status.service = NavSatStatus.SERVICE_GPS
            fix.latitude = latitude
            fix.longitude = longitude
            fix.altitude = 0.0
            fix.position_covariance = [
                1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 2.0,
            ]
            fix.position_covariance_type = NavSatFix.COVARIANCE_TYPE_DIAGONAL_KNOWN
            writer.write('/fix/valid', serialize_message(fix), timestamp_ns)

        del writer
        gc.collect()

        generated_files = list(bag_directory.glob('*.mcap'))
        if len(generated_files) != 1:
            raise RuntimeError(
                f'Expected one generated MCAP file, found {len(generated_files)}'
            )
        shutil.copyfile(generated_files[0], output)

    print(f'Generated {output}')
    print('Route: 450 m clockwise circle around 52.0494, 4.7521')
    print('Water temperature: 12 + 10 * sin(bearing) deg C')
    print('Sonar: 8 + 2.5 * cos(2*bearing) + 0.5 * sin(5*bearing) m')
    print('BT785 conductivity: 450 + 120 * sin(bearing + pi/4) uS/cm')
    print('BT785 temperature: water temperature + 0.35 * cos(2*bearing) deg C')


if __name__ == '__main__':
    generate(parse_args().output)
