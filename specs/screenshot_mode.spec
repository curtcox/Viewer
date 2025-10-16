# Screenshot mode showcases

## CID demo renders when enabled
* When I request /_screenshot/cid-demo with screenshot mode enabled
* The response status should be 200
* The CID screenshot response should include expected content

## Upload and server event showcases render sample content
* When I request /_screenshot/uploads with screenshot mode enabled
* The response status should be 200
* The uploads screenshot response should include sample data
* When I request /_screenshot/server-events with screenshot mode enabled
* The response status should be 200
* The server events screenshot response should include sample data
