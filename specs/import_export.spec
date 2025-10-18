# Import and export

## Users can transport functionality between sites
* Given an origin site with a server named "shared-tool" returning "Hello from origin"
* And I export servers and their CID map from the origin site
* When I import the exported data into a fresh destination site
* Then the destination site should have a server named "shared-tool"
* And executing "/shared-tool" on the destination site should return "Hello from origin"
