import { GeoJSON } from "@foxglove/schemas";

import { Input, Time } from "./types.ts";

export const inputs = ["/fix/valid", "/sonar"];
export const output = "/analysis/sonar_route";

type GpsInput = Input<"/fix/valid">;
type MeasurementInput = Input<"/sonar">;
type Coordinate = [longitude: number, latitude: number];

const MAX_MEASUREMENT_AGE_SECONDS = 2;
const MAX_GPS_GAP_SECONDS = 10;
const VALUE_MIN = 5;
const VALUE_MAX = 11;

let latestValue: number | undefined;
let latestMeasurementTime: number | undefined;
let previousPosition: Coordinate | undefined;
let previousGpsTime: number | undefined;

function stampToSeconds(stamp: Time): number {
  return stamp.sec + stamp.nsec / 1_000_000_000;
}

function channelToHex(value: number): string {
  return Math.round(value).toString(16).padStart(2, "0");
}

function valueColor(value: number): string {
  const fraction = Math.max(
    0,
    Math.min(1, (value - VALUE_MIN) / (VALUE_MAX - VALUE_MIN)),
  );
  const cold = [49, 54, 149];
  const warm = [215, 48, 39];
  const rgb = cold.map(
    (channel, index) => channel + fraction * (warm[index] - channel),
  );
  return `#${rgb.map(channelToHex).join("")}`;
}

export default function script(
  event: GpsInput | MeasurementInput,
): GeoJSON | undefined {
  if (event.topic === "/sonar") {
    const value = event.message.range;
    if (Number.isFinite(value)) {
      latestValue = value;
      latestMeasurementTime = stampToSeconds(event.message.header.stamp);
    }
    return;
  }

  const gpsTime = stampToSeconds(event.message.header.stamp);
  const latitude = event.message.latitude;
  const longitude = event.message.longitude;

  if (
    event.message.status.status < 0 ||
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude)
  ) {
    previousPosition = undefined;
    previousGpsTime = undefined;
    return;
  }

  if (
    previousGpsTime !== undefined &&
    (gpsTime <= previousGpsTime || gpsTime - previousGpsTime > MAX_GPS_GAP_SECONDS)
  ) {
    previousPosition = undefined;
  }

  const currentPosition: Coordinate = [longitude, latitude];
  const measurementAge =
    latestMeasurementTime === undefined
      ? Number.POSITIVE_INFINITY
      : gpsTime - latestMeasurementTime;

  if (
    previousPosition === undefined ||
    latestValue === undefined ||
    measurementAge < 0 ||
    measurementAge > MAX_MEASUREMENT_AGE_SECONDS
  ) {
    previousPosition = currentPosition;
    previousGpsTime = gpsTime;
    return;
  }

  const segmentStart = previousPosition;
  previousPosition = currentPosition;
  previousGpsTime = gpsTime;

  return {
    geojson: JSON.stringify({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {
            name: "Sonar depth",
            metadata: {
              "Depth": `${latestValue.toFixed(2)} m`,
              "Sample age": `${measurementAge.toFixed(1)} s`,
            },
            style: {
              color: valueColor(latestValue),
              dashArray: "12 6",
              lineCap: "round",
              opacity: 0.65,
              weight: 14,
            },
          },
          geometry: {
            type: "LineString",
            coordinates: [segmentStart, currentPosition],
          },
        },
      ],
    }),
  };
}
