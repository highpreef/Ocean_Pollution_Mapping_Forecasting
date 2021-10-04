"""
Author: David Jorge

This is the app script for launching the dashboard for the Ocean Pollution and Forecasting Project.
"""

import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
from dash.dependencies import Input, Output
import forecasting
import pullS3

# Load mapbox token
token = os.getenv("MAPBOX_TOKEN")
if not token:
    token = open(".mapbox_token").read()
px.set_mapbox_access_token(open(".mapbox_token").read())

# Initialize dashboard
app = dash.Dash(__name__)
app.config.suppress_callback_exceptions = True
app.title = "Ocean Pollution Tracking Dashboard"

# Initialize AWS API library
aws = pullS3.pullS3()
aws.pull()

# Initialize the forecasting simulation library and run initial simulation
fc = forecasting.forecasting(aws.map_data['lat'].tolist(), aws.map_data['lon'].tolist(), "particle_sim.nc")
fc.run_forecasting(days=14)
fc.output_sim()

# Initialize initial map section on the dashboard with data from the AWS API
fig = px.scatter_mapbox(aws.map_data, lat="lat", lon="lon", hover_name="Date",
                        hover_data=["Number of Clusters", "temp", "humidity", "pressure", "pitch", "roll",
                                    "yaw"],
                        color="Number of Clusters", size="_size_",
                        color_continuous_scale=px.colors.cyclical.IceFire, size_max=15, zoom=3, height=500)
# fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

# Define the dashboard HTML layout
app.layout = html.Div(
    children=[
        html.Div(className='row',
                 children=[
                     html.Div(className='four columns div-user-controls',
                              children=[
                                  html.P(children="🌊", className="header-emoji"),
                                  html.H1(
                                      children="Ocean Pollution Analytics", className="header-title"
                                  ),
                                  html.P(
                                      children="Analyze the output of the Ocean Pollution Drones"
                                               " stored in AWS.",
                                      className="header-description",
                                  ),
                              ]
                              ),
                     html.Div(className='eight columns div-for-charts bg-grey',
                              children=[
                                  html.Div(
                                      children=[
                                          html.H2(
                                              [
                                                  "Pollution Map",
                                              ],
                                              style={
                                                  "font-size": "28px",
                                                  "font-weight": "bold",
                                              },
                                          ),
                                          dcc.Graph(
                                              id="map-graph",
                                              figure=fig,
                                          ),
                                      ],
                                      style={
                                          "width": "98%",
                                          "margin-right": "0",
                                      },
                                      id="map-div",
                                  ),
                                  html.Div(
                                      children=[
                                          html.H2(
                                              [
                                                  "Forecasting Drift 14 Days Ahead",
                                              ],
                                              style={
                                                  "font-size": "28px",
                                                  "font-weight": "bold",
                                              },
                                          ),
                                          html.Video(
                                              id="live-update-forecasting",
                                              src=app.get_asset_url("sim.mp4"),
                                              autoPlay=True,
                                              controls=True,
                                              loop=True,
                                              style={
                                                  # "display": "block",
                                                  # "margin-left": "auto",
                                                  # "margin-right": "auto",
                                                  "max-width": "100%",
                                                  # "width": "70%",
                                              },
                                          )
                                      ],
                                      style={
                                          "width": "98%",
                                          "margin-right": "0",
                                          # "margin-bottom": "50",
                                          # "max-height": "50px",
                                      },
                                      id="forecast-div",
                                  ),
                                  html.Div(
                                      children=[
                                          html.H2(
                                              [
                                                  "Hourly Detections",
                                              ],
                                              style={
                                                  "font-size": "28px",
                                                  "font-weight": "bold",
                                              },
                                          ),
                                          dcc.Graph(
                                              id="bar-graph",
                                              figure={
                                                  "data": [
                                                      {"x": aws.hourly["Date"], "y": aws.hourly["Count"],
                                                       "type": "bar", },
                                                  ],
                                                  "layout": {
                                                      "xaxis": {"fixedrange": True},
                                                      "yaxis": {
                                                          "fixedrange": True,
                                                      },
                                                      "colorway": ["#E12D39"],
                                                  },
                                              }
                                          ),
                                      ],
                                      style={
                                          "width": "98%",
                                          "margin-right": "0",
                                      },
                                      id="bar-div",
                                  ),
                                  html.Div(
                                      children=[
                                          html.H2(
                                              [
                                                  "Latest Snapshot",
                                              ],
                                              style={
                                                  "font-size": "28px",
                                                  "font-weight": "bold",
                                              },
                                          ),
                                          html.Img(
                                              id="live-update-img",
                                              src=app.get_asset_url("{}.png".format(aws.mostRecent)),
                                              style={
                                                  "display": "block",
                                                  "margin-left": "auto",
                                                  "margin-right": "auto",
                                                  # "width": "50%",
                                              },
                                          )
                                      ],
                                      style={
                                          "width": "98%",
                                          "margin-right": "50",
                                          "margin-bottom": "50",
                                          "max-height": "50px",
                                      },
                                      id="img-div",
                                  ),
                                  dcc.Interval(
                                      id='interval',
                                      interval=60 * 2000,  # in milliseconds
                                      n_intervals=0
                                  ),
                              ])
                 ])
    ]

)


# Define callback function to implement live update of data on the dashboard.
@app.callback(Output(component_id='live-update-img', component_property='src'),
              Output(component_id='live-update-forecasting', component_property='src'),
              Output(component_id="bar-graph", component_property="figure"),
              Output(component_id="map-graph", component_property="figure"),
              Input(component_id='interval', component_property='n_intervals'))
def update(n_intervals):
    # Get up to date data
    aws.pull()

    # Run simulation with new data
    fc.update_particles(aws.map_data['lat'].tolist(), aws.map_data['lon'].tolist())
    fc.run_forecasting(days=14)
    fc.output_sim()

    # Update hourly detections bar graph
    updatedFigHourly = {
        "data": [
            {"x": aws.hourly["Date"], "y": aws.hourly["Count"], "type": "bar", },
        ],
        "layout": {
            "xaxis": {"fixedrange": True},
            "yaxis": {
                "fixedrange": True,
            },
            "colorway": ["#E12D39"],
        },
    }

    # Update dashboard map
    updatedMapFig = px.scatter_mapbox(aws.map_data, lat="lat", lon="lon", hover_name="Date",
                                      hover_data=["Number of Clusters", "temp", "humidity", "pressure", "pitch", "roll",
                                                  "yaw"],
                                      color="Number of Clusters", size="_size_",
                                      color_continuous_scale=px.colors.cyclical.IceFire, size_max=15, zoom=3,
                                      height=500)
    # fig.update_layout(mapbox_style="open-street-map")
    updatedMapFig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return app.get_asset_url("{}.png".format(aws.mostRecent)), app.get_asset_url(
        "sim.mp4"), updatedFigHourly, updatedMapFig


if __name__ == "__main__":
    app.run_server(debug=False)
