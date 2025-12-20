# Server detail page

## Server detail page is accessible
* Given there is a server named weather returning Weather forecast ready
* When I request the page /servers/weather
* Path coverage: /servers/weather
* The response status should be 200
* The page should contain Edit Server
* The page should contain Server Definition
* The page should contain Back to Servers

## Server config tab summarizes named values
* Given there is a server named weather returning Weather forecast ready
* When I request the page /servers/weather
* The page should contain Config
* The page should contain Named value configuration
* The page should contain No named values were detected for this server.
