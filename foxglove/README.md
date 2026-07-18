# Foxglove resources

This directory contains project resources for inspecting Karaburan MCAP
recordings in Foxglove.

```text
foxglove/
|-- README.md
|-- demo/
|   |-- generate_demo_mcap.py
|   `-- reeuwijk-surfplas-temperature.mcap
|-- layouts/
|   `-- README.md
`-- user-scripts/
    |-- bt785-temperature-route.ts
    |-- conductivity-route.ts
    |-- sonar-route.ts
    `-- temperature-route.ts
```

## Measurement route demo

The demo combines recorded GPS fixes with several synthetic water and distance
measurements. The user script renders the route with a temperature-based color.

The data is synthetic. It follows a clockwise circle with a radius of 450 m
around latitude `52.0494`, longitude `4.7521`, the approximate center of the
[Surfplas](https://www.openstreetmap.org/way/93855919) at the Reeuwijkse
Plassen. The route is for visualization only and must not be used for
navigation.

The radial compass bearing is measured clockwise from north. The generated
temperature is:

```text
temperature = 12 + 10 * sin(bearing from center) degrees Celsius
```

This gives 12 degrees north of the center, 22 degrees east, 12 degrees south,
and 2 degrees west. GPS fixes are recorded at 1 Hz. Temperature is recorded at
0.2 Hz, matching the planning rate used by Karaburan. The script applies the
latest temperature to subsequent GPS route segments.

The complete measurement set contains:

| Measurement | Topic and field | Rate | Synthetic range |
|---|---|---:|---:|
| Standalone water temperature | `/temperature.temperature` | 0.2 Hz | 2.000-22.000 degrees C |
| Sonar depth | `/sonar.range` | 1 Hz | 5.000-10.732 m |
| Electrical conductivity | `/bt785.conductivity` | 0.1 Hz | 330.457-569.543 uS/cm |
| BT785 probe temperature | `/bt785.temperature` | 0.1 Hz | 1.650-21.650 degrees C |

Sonar depth varies with two combined waves around the circle. Conductivity is
`450 + 120 * sin(bearing + pi/4)` uS/cm. The BT785 temperature follows the
water-temperature curve with a small direction-dependent sensor difference.
These values are deliberately synthetic and demonstrate synchronized
visualization; they are not measurements of the real Surfplas.

### Open the demo

1. Start Foxglove Desktop or open the Foxglove web app.
2. Select **Open local file** and open
   `foxglove/demo/reeuwijk-surfplas-temperature.mcap`.
3. Open the right sidebar with `]`, select **User Scripts**, and create a script.
4. Copy all of `user-scripts/temperature-route.ts` into the editor and save it
   with `Ctrl+S`.
5. Create three more User Scripts, copying one repository file into each:
   `sonar-route.ts`, `conductivity-route.ts`, and
   `bt785-temperature-route.ts`.
6. Add a **Map** panel.
7. Enable the desired route topics in the Map panel topic settings:
   - `/analysis/temperature_route`;
   - `/analysis/sonar_route`;
   - `/analysis/conductivity_route`;
   - `/analysis/bt785_temperature_route`.
8. Set each enabled route's **Time range** to **All previous** to watch it appear
   during playback, or **All** to see the complete route immediately.
9. Hover over a route segment to inspect its value and sample age.

The routes use different widths and dash patterns because they occupy the same
geographic path. Toggle topics or change their order in the Map panel when one
route obscures another.

The color scale used by the user script is:

| Temperature | Color |
|---:|---|
| 2 degrees C | Dark blue |
| 7 degrees C | Blue |
| 12 degrees C | Light blue |
| 17 degrees C | Yellow |
| 22 degrees C | Red |

Add a **Plot** panel for a second view of the source data:

- `/temperature.temperature` shows the measured temperature;
- `/sonar.range` shows sonar depth in meters;
- `/bt785.conductivity` shows electrical conductivity in uS/cm;
- `/bt785.temperature` shows the BT785 probe temperature;
- `/demo/bearing_from_center_deg.data` shows the radial compass bearing.

The Map panel can also display `/fix/valid` directly. Enable it temporarily to
compare the original GPS points with the derived colored route.

User scripts only run when their output topic is used by a panel. If the route
does not appear, add a **Raw Messages** panel for
one of the `/analysis/*_route` topics and check the User Scripts error and log
areas. Raw `/sonar` and `/bt785` topics cannot be added directly to a Map
panel because they do not contain geographic data.

### Use the script with a real recording

The script expects the topic names and message types currently recorded by
Karaburan:

| Topic | ROS 2 type | Purpose |
|---|---|---|
| `/fix/valid` | `sensor_msgs/msg/NavSatFix` | Validated GPS position |
| `/temperature` | `sensor_msgs/msg/Temperature` | Water temperature |
| `/sonar` | `sensor_msgs/msg/Range` | Sonar depth |
| `/bt785` | `karaburan_msgs/msg/ElectricalConductivity` | Conductivity and probe temperature |

Record with `with_temperature:=true` and one of the existing MCAP recording
profiles. The script rejects invalid GPS fixes, temperature samples older than
10 seconds, and GPS gaps longer than 10 seconds. Adjust these constants near the
top of `temperature-route.ts` if the real sensor cadence changes.

### Regenerate the demo MCAP

The generator uses the ROS 2 Jazzy environment from the repository test image.
From the repository root in PowerShell, first build that image if necessary:

```powershell
docker build --pull --no-cache -f docker/Dockerfile.ros-jazzy-test -t karaburan-ros-test .
```

Then regenerate the committed demo file:

```powershell
docker run --rm --mount "type=bind,source=$($PWD.Path),target=/workspace" karaburan-ros-test bash -lc "source /opt/ros/jazzy/setup.bash && source /karaburan/ros_ws/install/setup.bash && python3 /workspace/foxglove/demo/generate_demo_mcap.py --output /workspace/foxglove/demo/reeuwijk-surfplas-temperature.mcap"
```

The generator writes ordinary ROS 2 CDR messages to MCAP, so the result can be
opened by both Foxglove and ROS 2 tooling.
