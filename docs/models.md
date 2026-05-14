# Epidemiological Models Documentation

Comprehensive guide to the epidemiological models supported by `laser-init`.

## Table of Contents

1. [Overview](#overview)
2. [Model Selection Guide](#model-selection-guide)
3. [SI Model](#si-model)
4. [SIR Model](#sir-model)
5. [SEIR Model](#seir-model)
6. [Model Parameters](#model-parameters)
7. [Spatial Connectivity](#spatial-connectivity)
8. [Vital Dynamics](#vital-dynamics)
9. [Running Simulations](#running-simulations)
10. [Extending Models](#extending-models)

## Overview

`laser-init` generates ready-to-run spatial disease models using the [LASER](https://github.com/laser-base/laser-generic) framework. The tool supports three classic compartmental model types:

- **SI** (Susceptible-Infectious)
- **SIR** (Susceptible-Infectious-Recovered)
- **SEIR** (Susceptible-Exposed-Infectious-Recovered)

All models are:

- **Spatial**: Disease spreads across administrative regions via gravity model
- **Stochastic**: Individual-level Monte Carlo simulation
- **Demographic**: Includes births and deaths based on vital statistics
- **Agent-based**: Tracks individuals with state transitions

## Model Selection Guide

### Quick Selection Matrix

| Disease Characteristic | Recommended Model |
|----------------------|-------------------|
| Permanent infection (e.g., HIV) | SI |
| Lifelong immunity (e.g., measles) | SIR |
| Temporary immunity (e.g., influenza) | SEIR or SEIRS* |
| Incubation period (e.g., COVID-19) | SEIR |
| Fast onset (e.g., norovirus) | SIR |
| Vector-borne (e.g., malaria) | Custom extension** |

\* SEIRS requires manual modification (see [Extending Models](#extending-models))

\*\* Requires custom LASER components

### Detailed Comparison

| Feature | SI | SIR | SEIR |
|---------|----|----|------|
| **Compartments** | 2 (S, I) | 3 (S, I, R) | 4 (S, E, I, R) |
| **Immunity** | None | Permanent | Permanent |
| **Incubation Period** | No | No | Yes |
| **Parameters** | 2 (R<sub>0</sub>, duration) | 2 (R<sub>0</sub>, duration) | 3 (R<sub>0</sub>, exposed duration, infectious duration) |
| **Computational Cost** | Lowest | Low | Medium |
| **Best For** | Chronic infections | Acute immunizing diseases | Diseases with latent period |

## SI Model

### Overview

The simplest epidemic model. Individuals are either Susceptible (S) or Infectious (I). Once infected, individuals remain infectious indefinitely.

### Compartments

```
S ── β ──> I
```

- **S (Susceptible)**: Can be infected
- **I (Infectious)**: Infected and can transmit to susceptibles

### State Transitions

1. **Infection**: S → I (rate = β × I / N)

where:
- β = transmission rate (R<sub>0</sub> / infectious_duration)
- I = number of infectious individuals
- N = total population

### Use Cases

- **HIV/AIDS** (without treatment)
- **Chronic diseases** with no recovery
- **Persistent infections**
- **Theoretical studies** of epidemic thresholds

### Equilibrium Behavior

- Infection prevalence grows until all susceptibles are infected
- No endemic equilibrium (unless balanced by births/deaths)
- Final size: 100% (in closed population)

### Generating an SI Model

```shell
laser-init KEN 2 2010 2020 --model SI
```

## SIR Model

### Overview

Classic epidemic model with recovery. Individuals move from Susceptible to Infectious to Recovered, acquiring permanent immunity.

### Compartments

```
S ── β ──> I ── γ ──> R
```

- **S (Susceptible)**: Can be infected
- **I (Infectious)**: Infected and transmitting
- **R (Recovered)**: Immune (permanent)

### State Transitions

1. **Infection**: S → I (rate = β × I / N)
2. **Recovery**: I → R (rate = γ = 1 / infectious_duration)

### Threshold Dynamics

**Basic Reproduction Number (R<sub>0</sub>)**: Average secondary infections from one case

- R<sub>0</sub> > 1: Epidemic occurs
- R<sub>0</sub> = 1: Endemic equilibrium
- R<sub>0</sub> < 1: Disease dies out

**Epidemic threshold**: Requires S0 > N/R<sub>0</sub> to start epidemic

### Use Cases

- **Measles, mumps, rubella** (lifelong immunity)
- **Chickenpox**
- **Smallpox** (historical)
- **SARS-CoV-1** (2002-2003)
- **Acute infections** with immunity

### Equilibrium Behavior

- Endemic equilibrium possible with births/deaths
- Final size < 100% (some susceptibles remain)
- Herd immunity threshold: 1 - 1/R<sub>0</sub>

### Generating an SIR Model

```shell
laser-init ETH 2 2010 2020 --model SIR
```

## SEIR Model

### Overview

Extended SIR model with exposed (latent) compartment. Individuals go through an incubation period (E) before becoming infectious (I).

### Compartments

```
S ── β ──> E ── σ ──> I ── γ ──> R
```

- **S (Susceptible)**: Can be infected
- **E (Exposed)**: Infected but not yet infectious (latent period)
- **I (Infectious)**: Infectious and transmitting
- **R (Recovered)**: Immune (permanent)

### State Transitions

1. **Infection**: S → E (rate = β × I / N)
2. **Progression**: E → I (rate = σ, from exposed duration distribution)
3. **Recovery**: I → R (rate = γ = 1 / infectious_duration)

### Latent Period Distribution

`laser-init` uses a **gamma distribution** for the exposed period (this is easily changed by editing the model script and using one of the [supported distributions](https://laser.idmod.org/laser-generic/reference/laser/core/distributions/)):

```python
exposed_duration ~ Gamma(shape, scale)
mean = shape × scale
variance = shape × scale²
```

Default parameters:
- shape = 4.5
- scale = 1.0
- mean = 4.5 days

### Use Cases

- **COVID-19** (2-5 day incubation)
- **Influenza** (1-4 day incubation)
- **Ebola** (8-10 day incubation)
- **MERS-CoV**
- **Most viral respiratory infections**

### Equilibrium Behavior

- Similar to SIR but delayed by latent period
- Peak occurs later than SIR with same R<sub>0</sub>
- Final size approximately same as SIR

### Generating an SEIR Model

```shell
laser-init NGA 2 2010 2020 --model SEIR  # Default model type
```

## Model Parameters

### Core Parameters

All models share these common parameters:

| Parameter | Symbol | Unit | Description | Typical Range |
|-----------|--------|------|-------------|---------------|
| **Basic Reproduction Number** | R<sub>0</sub> | dimensionless | Average secondary infections | 1.5 - 20+ |
| **Infectious Duration** | 1/γ | days | Mean time infectious | 1 - 30 days |
| **Simulation Duration** | T | years | Length of simulation | 1 - 50 years |

### SEIR-Specific Parameters

| Parameter | Symbol | Unit | Description | Typical Range |
|-----------|--------|------|-------------|---------------|
| **Exposed Duration Shape** | k | dimensionless | Gamma distribution shape | 2 - 10 |
| **Exposed Duration Scale** | θ | days | Gamma distribution scale | 0.5 - 5 days |

### Derived Parameters

Automatically calculated:

- **Transmission rate**: β = R<sub>0</sub> / infectious_duration
- **Recovery rate**: γ = 1 / infectious_duration
- **Progression rate**: σ ~ Gamma(shape, scale)
- **Total ticks**: nticks = nyears × 365

### Disease-Specific Parameters

Examples for common diseases:

#### Influenza
- R<sub>0</sub>: 1.5 - 2.5
- Exposed period: 1-4 days (shape=3, scale=0.7)
- Infectious period: 5-7 days

#### COVID-19 (Original)
- R<sub>0</sub>: 2.5 - 3.5
- Exposed period: 3-5 days (shape=4.5, scale=1.0)
- Infectious period: 7-10 days

#### Measles
- R<sub>0</sub>: 12 - 18
- Exposed period: 10-12 days
- Infectious period: 8 days

#### Ebola
- R<sub>0</sub>: 1.5 - 2.5
- Exposed period: 8-10 days
- Infectious period: 10 days

## Spatial Connectivity

All models include spatial coupling via a **gravity model**.

### Gravity Model Formula

Movement rate between regions i and j:

$M_{i,j} = \kappa \times \frac {(P^a_i \times P^b_j)} {d_{i,j}^c}$

where:

- κ = scaling constant
- P<sub>i</sub>, P<sub>j</sub> = populations of regions i and j
- d(i,j) = distance between regions
- a = source population, P<sub>i</sub>, exponent (typically 1)
- b = destination population, P<sub>j</sub>, exponent (typically 1)
- c = distance exponent (typically 1-2)

### Spatial Transmission

Infections can occur:

1. **Locally**: Within the same administrative region (most common)
2. **Via mobility**: Through movement between regions (gravity model)

Effective transmission rate:
```
β_effective = β_local + β_spatial
```

### Customizing Spatial Parameters

Currently, gravity model parameters are hard-coded in the generated model scripts. To modify:

```python
# In seir.py (or sir.py, si.py)
# Add after model initialization:

from laser.generic.movement import GravityModel

gravity = GravityModel(
    model,
    kappa=0.001,      # Scaling constant
    alpha=2.0,        # Distance exponent
    max_distance=500  # km, optional distance cutoff
)

model.components.append(gravity)
```

## Vital Dynamics

All generated models include births and deaths based on demographic data.

### Births

- **Rate**: Crude Birth Rate (CBR) from UN WPP
- **Distribution**: Age distribution from UN WPP (base year)
- **Assignment**: New births distributed across regions proportional to population

#### Implementation

```python
from laser.generic.vitaldynamics import BirthsByCBR
from laser.core.demographics import AliasedDistribution

# Age distribution for new births
pyramid = AliasedDistribution(pop_df.PopTotal.to_numpy())

# Birth rates over time
birthrates = ValuesMap.from_timeseries(daily_cbr, len(scenario))

# Add births component
births = BirthsByCBR(model, birthrates, pyramid)
model.components.append(births)
```

### Deaths

- **Rate**: Based on life table from UN WPP
- **Distribution**: Age-specific mortality via Kaplan-Meier estimator
- **Implementation**: Survival curves applied to all compartments

#### Implementation

```python
from laser.generic.vitaldynamics import MortalityByEstimator
from laser.core.demographics import KaplanMeierEstimator

# Life table survival curve
survival = KaplanMeierEstimator(exp_df.cumulative_deaths.to_numpy())

# Add mortality component
mortality = MortalityByEstimator(model, survival)
model.components.append(mortality)
```

### Demographic Effects

With vital dynamics:

- **Population growth**: Can increase or decrease over simulation
- **Age structure**: Maintained via age-specific births/deaths
- **Endemic equilibrium**: Disease can persist via birth of new susceptibles
- **Long-term dynamics**: Demographic changes affect epidemic patterns

## Running Simulations

### Basic Execution

```shell
cd KEN/2010
python3 ./seir.py
```

If you generated a different model with `--model`, run `python3 ./si.py` or `python3 ./sir.py` instead.

### With Custom Config

```shell
python3 ./seir.py --config custom_config.yaml
```

Use the matching script name here if you generated `si.py` or `sir.py`.

### With Custom Data Directory

```shell
python3 ./seir.py --data-dir /path/to/data
```

Use the matching script name here if you generated `si.py` or `sir.py`.

### Output

Models generate plots in the output directory:
- Compartment dynamics (S, E, I, R over time)
- Spatial spread (choropleth snapshots)
- Effective reproduction number (Rt)
- Individual region trajectories
- Final attack rates

See [User Guide](userguide.md#interpreting-results) for detailed interpretation.

## Extending Models

### Adding Interventions

#### Vaccination Campaign

```python
# In generated model script, after components definition

class Vaccination:
    def __init__(self, model, start_day, rate, efficacy=1.0):
        self.model = model
        self.start_day = start_day
        self.rate = rate  # Daily vaccination rate
        self.efficacy = efficacy

    def apply(self):
        if self.model.tick >= self.start_day:
            # Vaccinate fraction of susceptibles
            to_vaccinate = (self.model.scenario.S * self.rate).astype(int)
            effective = (to_vaccinate * self.efficacy).astype(int)

            self.model.scenario.S -= effective
            self.model.scenario.R += effective

# Add to model
vaccination = Vaccination(model, start_day=365, rate=0.01, efficacy=0.9)
model.components.append(vaccination)
```

#### Social Distancing

```python
class SocialDistancing:
    def __init__(self, model, start_day, end_day, reduction):
        self.model = model
        self.start_day = start_day
        self.end_day = end_day
        self.reduction = reduction  # e.g., 0.5 for 50% reduction
        self.original_beta = None

    def apply(self):
        if self.model.tick == self.start_day:
            self.original_beta = self.model.params.beta
            self.model.params.beta *= (1 - self.reduction)
        elif self.model.tick == self.end_day:
            self.model.params.beta = self.original_beta

# Add to model
distancing = SocialDistancing(model, start_day=180, end_day=270, reduction=0.5)
model.components.append(distancing)
```

### Converting SEIR to SEIRS (Waning Immunity)

```python
# Add after SEIR component definitions

class WaningImmunity:
    def __init__(self, model, waning_rate):
        self.model = model
        self.waning_rate = waning_rate  # Daily rate of immunity loss

    def apply(self):
        # Move R back to S based on waning rate
        to_wane = (self.model.scenario.R * self.waning_rate).astype(int)
        self.model.scenario.R -= to_wane
        self.model.scenario.S += to_wane

# Add to model (after r component)
waning = WaningImmunity(model, waning_rate=1/365)  # 1-year average immunity
model.components.insert(-1, waning)  # Insert before mortality
```

### Adding Age Structure

```python
# Modify initialization to track age groups
age_groups = ["0-4", "5-14", "15-64", "65+"]
for age in age_groups:
    scenario[f"S_{age}"] = initial_population_by_age[age]
    scenario[f"I_{age}"] = 0
    scenario[f"R_{age}"] = 0

# Modify transmission to account for age-specific contact matrices
# (requires more extensive modification - see LASER documentation)
```

## Mathematical Background

### Basic Reproduction Number (R<sub>0</sub>)

Definition: Average number of secondary infections from one infectious individual in a fully susceptible population.

**Interpretation**:

- R<sub>0</sub> = 2: Each case infects 2 others on average
- R<sub>0</sub> > 1: Epidemic growth
- R<sub>0</sub> = 1: Endemic equilibrium
- R<sub>0</sub> < 1: Disease extinction

**Calculation**: R<sub>0</sub> = β / γ = β × infectious_duration

**Herd immunity threshold**: $H = 1 - 1/R_0$

### Effective Reproduction Number (Rt)

Time-varying reproduction number accounting for depletion of susceptibles:

$R_t = R_0 \times (S(t) / N)$

When R<sub>t</sub> < 1, epidemic is declining.

### Attack Rate

Proportion of population infected over the entire epidemic:

```
Attack Rate = (R_final - R_initial) / N
```

## Model Validation

### Calibration Approaches

1. **Literature values**: Use published R<sub>0</sub> and duration parameters
2. **Historical fit**: Calibrate to past outbreak data
3. **Expert elicitation**: Consult epidemiologists for parameter ranges
4. **Sensitivity analysis**: Test parameter uncertainty

### Validation Checks

- [ ] Peak timing reasonable for disease?
- [ ] Attack rate within expected range?
- [ ] Spatial spread patterns realistic?
- [ ] Compartment totals sum to population?
- [ ] No negative population values?
- [ ] Demographics match input data?

## Further Reading

### Compartmental Models
- Keeling & Rohani (2008). *Modeling Infectious Diseases in Humans and Animals*. Princeton University Press.
- Vynnycky & White (2010). *An Introduction to Infectious Disease Modelling*. Oxford University Press.

### Spatial Models
- Riley (2007). Large-scale spatial-transmission models of infectious disease. *Science*, 316(5829), 1298-1301.
- Balcan et al. (2009). Multiscale mobility networks and the spatial spreading of infectious diseases. *PNAS*, 106(51), 21484-21489.

### LASER Framework

- [laser-core](https://github.com/laser-base/laser-core)
- [laser-generic](https://github.com/laser-base/laser-generic)
- [LASER documentation](https://laser.idmod.org/laser-generic/)

## Support

For model questions:

- [User Guide](userguide.md) - Comprehensive workflows
- [Configuration Guide](configuration.md) - Parameter reference
- [GitHub Issues](https://github.com/laser-base/laser-init/issues) - Technical support

---

**Last Updated**: March 2026
