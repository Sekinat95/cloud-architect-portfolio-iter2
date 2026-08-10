# Long Short Term Memory (LSTM) and Gaussain Process (GP) Extended Reality(XR) User Equipment(UE) Energy Efficiency(EE)

## Introduction
This is the replication of a project I designed and implemented during my PhD in distributed systems and applied machine learning.
### Cellular Network Overview
#### EE for XR
#### ML-driven EE

### Architectural Overview
The overview of the end to end pipeline of the XR EE system(ML-side) is available at:

```mermaid
graph TD
  GCS["Raw XR service time series data"] --> EEPL
    subgraph EEPL["End-to-end pipeline"]
      PRS["Processed data"] -->GP & LSTM
      GP["Guassian process regression <br/> training"] --> GPOUT
      LSTM["Long Short Term Memory <br/> training"] --> LSTMOUT
      GPOUT["GP Batch Inference"] --> MDLUGP
      LSTMOUT["LSTM Batch Inference"] --> MDLULSTM
      MDLUGP["GP Model upload <br/> VA Model Registry"] --> TEST
      MDLULSTM["LSTM Model Upload"] --> TEST
    end
    subgraph TEST["Metric Calculations "]
    end
    subgraph TRDWN["Tear down"]
    end

  GCS --> EEPL --> TEST --> TRDWN
```
## Scope
### Sections and Components
#### Monitoring
## Results
### Metric Results

