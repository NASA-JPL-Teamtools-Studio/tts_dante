# Dante
Derivation Assistant for Novel Telemetry Expression

![Project logo](https://github.com/NASA-JPL-Teamtools-Studio/teamtools_documentation/blob/main/docs/images/tts_image_artifacts/dante.png)

## About Teamtools Studio

HTML Utilities is part of JPL's Teamtools Studio (TTS).

TTS is an effort originated in JPL's Planning and Execution section to centralize shared repositories across missions. This benefits JPL by reducing cost through reducing duplicated code, collaborating across missions, and unifying standards for development and design across JPL.

Although Planning and Execution is primarily concerned with flight operations, the TTS suite has been generalized and atomized to the point where many of these tools are applicable during other mission phases and even in non-spaceflight contexts. Through our work flying space missions, we hope to provide tools to the open source community that have utility in data analysis or planning for any complex system where failure is not an option.

For more infomation on how to contribute, and how these libraries form a complete ecosystem for high reliability data analysis, see the [Full TTS Documentation](https://nasa-jpl-teamtools-studio.github.io/teamtools-documentation/).

## What is HTML Utilities?

### Overview

Dante is the TTS answer to when a system that produces data doesn't produce the data that you want. The most typical need for Dante at JPL
is creating ground derived channels if those are not yet available in your project's GDS for any reason.

For those outside of JPL, a primer... AMPCS is the software used to connect with the DSN, decomm telemetry, and turn it into time
series data. AMPCS has a notion of "ground derived channels" (think dn to eu conversion as a simple example). AMPCS can combine
data from the spacecraft to make new channels that the spacecraft has no knowledge of, and Dante serves a very similar funciton.

This is not meant to be a replacement for AMPCS Ground Derived Channels, but as an admission that the AMPCS GDC infrastructure 
has its pros as well as cons. Pseudo-channels in this library will NEVER flow back into legacy CHILL databases, but may be 
put into tools like EAS's State Data Store for query later. 

Reasons you'd want to have Dante:

* GDS budgets and schedules are such that your Java-derived channel is not ready and you need something like it NOW
* You want to derive a channel in a way that is not possible or is prohibitively hard in the AMPCS Java layer (e.g. using data products in a complex way)
* You have a complex enough channel that you find it more tractible to just have your team do it rather than have to communicate from your team to GDS to your team.

Reasons you'd want to use AMPCS instead:

* Bit-derived channels. Unless using Dante as a workaround, DON'T put bit derived channels here as that subverts many assumptions about how those should work.
* Channels that you need to see in Chill/Chillax queries. There is some chance that SysQuery could help us here, but that's work to go with a lot of moving parts, so don't count on it.
* If you believe that the formal V&V that is inherent in the AMPCS GDC process is valuable. Keep in mind that any channels derived with Dante will be done at the TEAMTOOL layer. That implies more flexibility, but also more risk.


### Projects Currently Supported

* NISAR Prototype

## Architecture

### TTS dependencies

* TTS Utilities
* TTS Data Utils
