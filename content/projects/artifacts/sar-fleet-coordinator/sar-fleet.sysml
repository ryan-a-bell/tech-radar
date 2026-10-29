// SAR Fleet Coordinator — system-of-systems architecture (SysML v2 textual)
package SARFleet {
    private import ScalarValues::*;
    private import ISQ::*;

    package Requirements {
        requirement def <'SAR-001'> SearchCoverage {
            doc /* The fleet shall cover a 25 nm^2 search area at POD >= 0.8 within 4 h. */
            attribute areaNm2 : Real;
            attribute targetPod : Real;
        }
        requirement def <'SAR-002'> ReTaskLatency {
            doc /* Re-tasking shall reach every craft within 30 s of a POD map update. */
        }
        requirement def <'SAR-003'> EnduranceMargin {
            doc /* Each assigned sweep shall leave >= 20% fuel/battery reserve for RTB. */
        }
        requirement def <'SAR-004'> DegradedComms {
            doc /* Craft shall continue the last valid tasking for 10 min on loss of link. */
        }
    }

    package Structure {
        port def TaskingPort {
            out item tasking : Tasking;
            in item status : CraftStatus;
        }
        port def SensorFeedPort {
            out item detections : Detection;
        }
        item def Tasking;
        item def CraftStatus;
        item def Detection;

        part def Craft {
            attribute endurance : DurationValue;
            attribute sensorFootprint : LengthValue;
            port tasking : ~TaskingPort;
            port sensors : SensorFeedPort;
        }
        part def UnmannedSurfaceVessel :> Craft;
        part def UAV :> Craft;

        part def GroundStation {
            port fleetLink : TaskingPort;
            part planner : SearchPlanner;
            part dashboard : FleetDashboard;
        }
        part def SearchPlanner {
            part driftModel : DriftModel;
            part allocator : TaskAllocator;
        }
        part def DriftModel;
        part def TaskAllocator;
        part def FleetDashboard;

        part fleet {
            part station : GroundStation;
            part usv[2] : UnmannedSurfaceVessel;
            part uav[4] : UAV;
            interface link1 connect station.fleetLink to usv.tasking;
            interface link2 connect station.fleetLink to uav.tasking;
        }
    }

    package Behavior {
        action def PlanSearch {
            in lkp : Position;
            out cells : SearchCell[*];
        }
        action def AllocateTasks;
        action def ReTask;
        item def Position;
        item def SearchCell;
    }

    package Trace {
        private import Requirements::*;
        private import Structure::*;
        satisfy SearchCoverage by fleet.station.planner;
        satisfy ReTaskLatency by fleet.station.fleetLink;
        satisfy EnduranceMargin by fleet.station.planner.allocator;
        allocate Behavior::PlanSearch to fleet.station.planner;
        allocate Behavior::AllocateTasks to fleet.station.planner.allocator;
    }
}
