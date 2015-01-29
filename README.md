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

## Example Output

    Approx SOF: 1090
    Approx PTS: 1st: 68 | 2nd: 58 | 3rd: 49 | 4th: 39 | 5th: 29
    
    +----+-----+---------------+---------+------+-------+------+------+------+
    | #  | Car | Name          | License |  iR  | Races | SPos | AFin | AInc |
    +----+-----+---------------+---------+------+-------+------+------+------+
    | 2  | sol | C Alain       |  B 2.21 | 2504 |   176 |   13 |  3   |  4   |
    | 1  | sol | K Deslauriers |  A 3.33 | 2565 |     2 |  365 |  3   |  4   |
    | 3  | sol | J Werveke     |  A 2.30 | 1888 |     2 |  709 |  5   |  3   |
    | 4  | sol | D Isaenko     |  D 3.31 | 1863 |     7 |  215 |  3   |  7   |
    | 5  | mx5 | R Soto2       |  D 2.36 | 1697 |    61 |   33 |  5   |  7   |
    | 6  | sol | C Wesemael    |  D 3.58 | 1512 |     5 |  753 |  5   |  5   |
    | 7  | sol | M Barcelos    |  D 3.29 | 1485 |     2 |  863 |  7   |  0   |
    | 8  | sol | F Hough       |  B 4.40 | 1378 |     3 |  254 |  5   |  2   |
    | 9  | mx5 | M Leo         |  D 2.44 | 1320 |     5 |  945 |  5   |  5   |
    | 10 | mx5 | J Davis2      |  D 2.61 | 1045 |     4 |  705 |  4   |  7   |
    | 11 | sol | M Nötzelmann  |  D 2.64 | 471  |     3 |  721 |  5   |  7   |
    +----+-----+---------------+---------+------+-------+------+------+------+
