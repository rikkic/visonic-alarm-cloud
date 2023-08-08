# Visonic Cloud
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home assistant integration for [Visonic Alarms](https://www.visonic.com/en-hp-new) using the cloud (app) access method.

## Setup
| **Name**        | **Description**                                                                        | **Default**             |
|-----------------|----------------------------------------------------------------------------------------|-------------------------|
| host            | Cloud/monitoring provider your app is linked to (will have been provided by installer) | visonic.tycomonitor.com |
| email           | Email used to sign in to app                                                           | -                       |
| password        | Password used to sign in to app                                                        | -                       |
| panel_id        | Panel ID (6 character alphanumeric serial)                                             | -                       |
| master_code     | Master user code (Supplementary codes will not work!)                                  | -                       |
| codeless_arm    | Allow arming of the panel in HomeAssistant without a code                              | True                    |
| codeless_disarm | Allow disarming of the panel in HomeAssistant without a code                           | False                   |
| update_interval | Update time in seconds to poll the provider                                            | 60                      |


## Improving
Lots of improvement scope, this is just the bare minimum to get it started. Off the top of my head:

* Find the alarm state name
* Support multiple partitions
* Get exit time if possible (App seems to know this)
* Feature parity with source library (https://github.com/bitcanon/visonicalarm)
* General tidying up of code
* Options Flow

## Testing

Tested only on the PowerMaster 10 G2.
