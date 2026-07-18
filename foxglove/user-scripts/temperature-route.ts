import { GeoJSON } from "@foxglove/schemas";

import { Input, Time } from "./types.ts";

export const inputs = ["/fix/valid", "/temperature"];
export const output = "/analysis/temperature_route";

type GpsInput = Input<"/fix/valid">;
type TemperatureInput = Input<"/temperature">;
type Coordinate = [longitude: number, latitude: number];

const MAX_TEMPERATURE_AGE_SECONDS = 10;
const MAX_GPS_GAP_SECONDS = 10;

const COLOR_STOPS = [
  { temperature: 2, rgb: [49, 54, 149] },
  { temperature: 7, rgb: [69, 117, 180] },
  { temperature: 12, rgb: [116, 173, 209] },
  { temperature: 17, rgb: [254, 224, 144] },
  { temperature: 22, rgb: [215, 48, 39] },
] as const;

let latestTemperature: number | undefined;
let latestTemperatureTime: number | undefined;
let previousPosition: Coordinate | undefined;
let previousGpsTime: number | undefined;

function stampToSeconds(stamp: Time): number {
  return stamp.sec + stamp.nsec / 1_000_000_000;
}

function channelToHex(value: number): string {
  return Math.round(value).toString(16).padStart(2, "0");
}

function temperatureColor(temperature: number): string {
  const first = COLOR_STOPS[0];
  const last = COLOR_STOPS[COLOR_STOPS.length - 1];

  if (temperature <= first.temperature) {
    return `#${first.rgb.map(channelToHex).join("")}`;
  }
  if (temperature >= last.temperature) {
    return `#${last.rgb.map(channelToHex).join("")}`;
  }

  for (let index = 1; index < COLOR_STOPS.length; index++) {
    const upper = COLOR_STOPS[index];
    const lower = COLOR_STOPS[index - 1];
    if (temperature <= upper.temperature) {
      const fraction =
        (temperature - lower.temperature) /
        (upper.temperature - lower.temperature);
      const rgb = lower.rgb.map(
        (channel, channelIndex) =>
          channel + fraction * (upper.rgb[channelIndex] - channel),
      );
      return `#${rgb.map(channelToHex).join("")}`;
    }
  }

  return "#000000";
}

export default function script(
  event: GpsInput | TemperatureInput,
): GeoJSON | undefined {
  if (event.topic === "/temperature") {
    if (Number.isFinite(event.message.temperature)) {
      latestTemperature = event.message.temperature;
      latestTemperatureTime = stampToSeconds(event.message.header.stamp);
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
  const temperatureAge =
    latestTemperatureTime === undefined
      ? Number.POSITIVE_INFINITY
      : gpsTime - latestTemperatureTime;

  if (
    previousPosition === undefined ||
    latestTemperature === undefined ||
    temperatureAge < 0 ||
    temperatureAge > MAX_TEMPERATURE_AGE_SECONDS
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
            name: "Measured water temperature",
            metadata: {
              Temperature: `${latestTemperature.toFixed(1)} deg C`,
              "Sample age": `${temperatureAge.toFixed(1)} s`,
            },
            style: {
              color: temperatureColor(latestTemperature),
              lineCap: "round",
              opacity: 0.9,
              weight: 6,
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
