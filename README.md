# Splunk for Nest Thermostats

## What is a Nest?
The Nest is a smart and self-learning thermostat device for your home's heating and cooling systems. Alongside an easy to use interface, it also includes an Android app, an iPhone app, and a browser-based app to let you view the status and control the device.

## What does this app do?

One of the "issues" I had with the web-based application was the limited amount of data and metrics it presented to you. On top of that, the data was locked-in - there was no data to export to feed into your own systems for further processing and long-term keeping. The Nest apps seem to only keep data for about 10 days.

This app includes a Splunk [Modular Input](http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModInputsIntro) that when provided with your Nest's login credentials will periodically poll the same APIs the Android, iPhone, and web apps connect to and pull down schedule, temperature, and many other metrics from the site.

The app provides a set of dashboards to visualize some, but not all, of the collected data. There's a lot of data, so feel free to explore everything under `sourcetype = nest` and see what you can come up with!

## Contributing
If you have any suggested improvements, feel free to issue me a pull request on GitHub:

* [https://github.com/Ricapar/splunk-app-nest](https://github.com/Ricapar/splunk-app-nest)

## Credits

* My wonderful fiancé, Erica Feldman, for suggesting the idea of Splunk-ing my Nest thermostat in the first place.
* Scott M. Baker (smbaker), the author of [pynest](https://github.com/smbaker/pynest) - a Python library that lets you control your nest via the command line. I used his Python code to help me understand exactly what was happening behind the scenes when talking to Nest.com. 

## Disclaimer
This app uses undocumented APIs on Nest.com's website. It is entirely possible that everything may break if they decide to update their APIs, which would likely break existing dashboards, or break the data collection altogether.

Although the script only scrapes data using read-only API endpoints, I am also not responsible if the script somehow sets your thermostat to extreme temperatures.

# Setting up the App
## Via inputs.conf

The most straight-forward way is to simply create an entry in inputs.conf. The pre-built dashboards are not hard-coded to any specific index, so feel free to use an index of your choosing. A recommended interval value should be around 300-600 seconds (5 to 10 minutes). 

    [nest://My Nest Thermostat]
    username = me@example.com
    password = mypassword
    interval = 300
    index = myIndex

## Via the Splunk Web GUI

Log into Splunk, and go to:

```Settings > Data Inputs > Nest Thermostat Information > Add New```

Fill in your username and password for  your Nest.com account. Make sure to check the **More Settings** box, and specify an interval. As mentioned above, an interval of 300 to 600 seconds is recommended.
