# qwen3-max-query_qwen3-max-answer

## 1. You are an expert in the field of Duplex Stainless Steel. You are tasked with extracting all experimental details from academic research articles in the DSS field. Please first draft a hierarchy of all the information that you would extract.

As an expert in duplex stainless steels (DSS), I propose the following comprehensive and hierarchical framework for extracting experimental details from academic research articles in this field. This structure ensures systematic capture of all critical variables that govern DSS performance, from composition through processing, microstructure, to final properties. The hierarchy is organized into five primary tiers, each with nested subcategories to reflect the multi-scale, interdependent nature of DSS behavior.

---

### **1. Material Specification**
This tier defines the base alloy and its compositional characteristics.

- **1.1. DSS Grade Classification**
  - Lean duplex (e.g., EN 1.4162, UNS S32101)
  - Standard duplex (e.g., EN 1.4462, UNS S31803/S32205)
  - Super duplex (e.g., UNS S32750, 2507)
  - Hyper-duplex (e.g., UNS S32707, 2707)
  - Additively manufactured variants (e.g., LPBF-processed DSS)

- **1.2. Chemical Composition**
  - Major alloying elements: Cr, Ni, Mo, N, Mn, Si, C
  - Residual/trace elements: Cu, W, Co, S, P
  - Calculated indices:
    - Pitting Resistance Equivalent Number (PREN = %Cr + 3.3×%Mo + 16×%N)
    - Ferrite Number (FN) or Schaeffler/Delong diagram estimates

---

### **2. Processing History**
This tier captures all fabrication and thermal treatments that influence microstructure.

- **2.1. Primary Fabrication Method**
  - Wrought processing (hot/cold rolling, forging)
  - Casting (sand, investment)
  - Additive manufacturing:
    - Laser Powder Bed Fusion (LPBF)
    - Directed Energy Deposition (DED)
    - Key AM parameters: laser power, scan speed, hatch spacing, layer thickness, interlayer temperature

- **2.2. Post-Processing Treatments**
  - Solution annealing: temperature (e.g., 1050°C), duration (e.g., 3 h), cooling rate (water quench vs. air cool)
  - Hot Isostatic Pressing (HIP): pressure, temperature, time
  - Stress relief or aging treatments (e.g., 700–900°C for precipitate studies)

- **2.3. Joining Processes**
  - Welding method (GTAW, GMAW, laser welding, etc.)
  - Heat input (kJ/mm)
  - Zones analyzed:
    - Fusion Zone (FZ)
    - Heat-Affected Zone (HAZ)—subdivided into coarse-grained and fine-grained regions
    - Base metal (BM)

---

### **3. Microstructural Characteristics**
This tier details phase constitution, morphology, and defect features.

- **3.1. Primary Phases**
  - Ferrite (δ): volume fraction (%), grain size, morphology (e.g., columnar, equiaxed), crystallographic orientation
  - Austenite (γ): volume fraction (%), morphology (grain boundary, Widmanstätten, intragranular), distribution

- **3.2. Phase Balance**
  - Ferrite-to-austenite ratio (target ~50:50; deviations noted)
  - Quantification method: EBSD, XRD, image analysis of etched OM/SEM

- **3.3. Secondary Phases & Precipitates**
  - Sigma (σ) phase: volume fraction, morphology, formation temperature (>850°C), location (ferrite/austenite interfaces)
  - Chi (χ) phase: typically forms at 700–750°C as σ precursor
  - Nitrides: Cr₂N, CrN—often in ferrite at grain boundaries
  - Carbides: M₂₃C₆—forms at ~650°C, Cr-depleting adjacent zones
  - Other: G-phase, R-phase (in high-alloy grades)

- **3.4. Defects & Anomalies**
  - Porosity (especially in AM samples)
  - Microcracks
  - Elemental segregation (e.g., Cr/Mo enrichment in ferrite, Ni/N in austenite)

---

### **4. Characterization & Analytical Techniques**
This tier documents how microstructural and compositional data were obtained.

- **4.1. Microscopy**
  - Optical Microscopy (OM) with etchants (e.g., KOH, glyceregia)
  - Scanning Electron Microscopy (SEM): secondary/backscattered electron imaging
  - Transmission Electron Microscopy (TEM): for nanoscale precipitates

- **4.2. Phase & Crystallographic Analysis**
  - Electron Backscatter Diffraction (EBSD): phase mapping, grain orientation, boundary character
  - X-ray Diffraction (XRD): quantitative phase analysis

- **4.3. Compositional Analysis**
  - Energy-Dispersive X-ray Spectroscopy (EDS)
  - Wavelength-Dispersive Spectroscopy (WDS)
  - Atom Probe Tomography (APT) for nanoscale segregation

- **4.4. Thermal Analysis**
  - Differential Scanning Calorimetry (DSC) for phase transformation temperatures

---

### **5. Resulting Properties**
This tier links microstructure to functional performance.

- **5.1. Mechanical Properties**
  - Tensile properties: yield strength (YS), ultimate tensile strength (UTS), elongation
  - Hardness: Vickers (HV), Rockwell
  - Toughness: Charpy V-notch impact energy (at various temperatures)
  - Fatigue and creep behavior (if reported)

- **5.2. Corrosion Resistance**
  - Pitting corrosion:
    - Critical pitting temperature (CPT)
    - Pitting potential (Eₚᵢₜ) from cyclic potentiodynamic polarization
    - ASTM G48 testing (ferric chloride immersion)
  - Electrochemical metrics:
    - Electrochemical Impedance Spectroscopy (EIS) parameters
    - Open-circuit potential (OCP) stability
  - Intergranular and stress corrosion cracking (SCC) resistance

- **5.3. Structure–Property Relationships**
  - Correlation of phase balance with strength/toughness
  - Impact of sigma/chi/nitrides on embrittlement and localized corrosion
  - Effect of AM-induced texture or porosity on anisotropic properties

---

This hierarchical framework ensures that extracted data are not only comprehensive but also contextually linked—enabling meta-analysis, machine learning model training, or design of new DSS processing routes. Each level informs the next: composition and processing dictate microstructure, which in turn governs mechanical and corrosion performance. Special attention must be paid to non-equilibrium conditions (e.g., as-built AM microstructures >98% ferrite) and the thermal sensitivity of DSS, where minor deviations in heat treatment can trigger deleterious phase formation.

