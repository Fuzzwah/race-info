# Race Info

Reports information on your rivals prior to an iRacing race.

The License and iRating of each driver is collected using the Session Info API.

An approximation of the strength of field is returned, along with a list of 
estimated championship points for finishing positions down to 5th.

The User ID is also grabbed and then used in combination with the Web API to 
pull stats for this series for each driver;

 - the number of races
 - their current standing in the series
 - their average finish in races for this series
 - the average number of incidents per races for this series

The system handles multiclass races and will give the SOF and PTS estimates for
the car which the user is driving.

The iRDelta column shows an estimate of how your iRating will change if you ended up in the corresponding position.

## Example Output

![](https://user-images.githubusercontent.com/13685818/82134066-6a87fa00-97c1-11ea-9c50-1970616cec8e.png)
