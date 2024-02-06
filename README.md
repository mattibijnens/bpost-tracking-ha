# BPost Tracking V2
 A component to integrate TrackTry into Home Assistant 
 
 
 Two possibilities for installation :

With HACS : go in HACS, click on Integrations, click on the three little dots at top of the screen and selection "custom repositories", add this github url, select "Integration" as repository, and click ADD.

Then go to the Integrations tab of HACS, and install the "BPost" integration.
 
Add to configuration.yml

sensor:
    - platform: bpost
      api_key: can_be_empty
