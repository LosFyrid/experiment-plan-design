# qwen3-max-query_qwen3-max-answer

## 1. You are an expert in the field of Duplex Stainless Steel. You are tasked with extracting all experimental details from academic research articles in the DSS field. Please first draft a hierarchy of all the information that you would extract.

As an expert in Duplex Stainless Steel (DSS), I propose the following comprehensive, hierarchical framework for extracting experimental details from academic research articles. This structure is designed to capture all scientifically relevant parameters that govern the composition, processing, microstructure, properties, and performance of DSS materials, enabling systematic data mining, comparative analysis, and materials informatics applications.

---

### **I. Material Identity and Composition**
   - **Base Alloy Designation**: UNS number (e.g., UNS S32205), commercial name (e.g., 2205, 2507), or custom alloy label.
   - **Nominal Chemical Composition** (wt.% or at.%):
     - Major elements: Fe, Cr, Ni, Mo, N, Mn, Si
     - Minor/trace elements: Cu, W, Co, C, S, P, B, rare earths
     - Interstitial elements: C, N, O, H (especially critical for nitrogen’s role in phase balance)
   - **Actual Measured Composition**: As-analyzed values (e.g., via ICP-OES, EDS, or combustion analysis), including batch-specific variations.

### **II. Sample Preparation and Processing History**
   - **Melting and Casting Method**: Vacuum induction melting (VIM), arc melting, industrial continuous casting, etc.
   - **Thermomechanical Processing**:
     - Hot/cold rolling: reduction ratio, temperature, pass schedule
     - Forging: temperature, strain rate, number of passes
   - **Heat Treatment Conditions**:
     - Solution annealing: temperature, time, cooling rate (e.g., water quench vs. air cool)
     - Aging/precipitation treatments: isothermal holds (e.g., 700–950 °C), time, atmosphere
     - Welding parameters (if applicable): process (GTAW, GMAW), heat input (kJ/mm), interpass temperature, post-weld heat treatment (PWHT)

### **III. Microstructural Characterization**
   - **Phase Constitution**:
     - Volume fraction of austenite (γ) and ferrite (α): measured via image analysis, EBSD, or magnetic methods (e.g., Feritscope®)
     - Secondary phases: σ, χ, R, Laves, Cr₂N, CrN, M₂₃C₆ (type, morphology, distribution)
   - **Grain Structure**:
     - Grain size (ASTM or equivalent), aspect ratio, orientation
     - Phase morphology: Widmanstätten, lamellar, globular, intragranular austenite
   - **Analytical Techniques Used**:
     - Optical microscopy (OM), scanning electron microscopy (SEM), electron backscatter diffraction (EBSD), transmission electron microscopy (TEM), X-ray diffraction (XRD)

### **IV. Mechanical Properties**
   - **Tensile Behavior**: Yield strength (YS), ultimate tensile strength (UTS), elongation, strain hardening exponent
   - **Hardness**: Vickers (HV), Rockwell (HRC), measured in different phases or overall
   - **Impact Toughness**: Charpy V-notch energy (J) at various temperatures (e.g., −40 °C to 25 °C)
   - **Fatigue and Fracture**: Fatigue limit, crack growth rate (da/dN), fracture toughness (K_IC or J_IC)
   - **Creep and Stress Rupture**: At elevated temperatures (if studied)

### **V. Corrosion and Environmental Performance**
   - **Test Environments**:
     - Chloride-containing (e.g., 3.5% NaCl, ASTM G48), acidic (H₂SO₄, HCl), alkaline, sour (H₂S/CO₂)
     - Temperature, pH, aeration, flow conditions
   - **Corrosion Metrics**:
     - Pitting Resistance Equivalent Number (PREN = %Cr + 3.3×%Mo + 16×%N)
     - Critical pitting temperature (CPT), critical crevice temperature (CCT)
     - Electrochemical parameters: E_corr, i_corr, breakdown potential (E_b), repassivation potential (E_rep)
     - Weight loss, pit depth distribution, intergranular corrosion (IGC) susceptibility (e.g., ASTM A262)
   - **Stress Corrosion Cracking (SCC)**: Threshold stress intensity (K_ISCC), time-to-failure under constant load or slow strain rate testing (SSRT)

### **VI. Experimental Conditions and Metadata**
   - **Standards Followed**: ASTM, ISO, NACE, or other relevant protocols
   - **Specimen Geometry and Orientation**: Longitudinal/transverse, as-rolled vs. heat-treated condition
   - **Replication and Statistics**: Number of replicates, error bars, confidence intervals
   - **Date and Source**: Publication year, institution, funding source (for provenance tracking)

### **VII. Computational or Modeling Inputs (if applicable)**
   - Thermodynamic calculations: Thermo-Calc® or JMatPro® predictions of phase stability
   - Kinetic models: Time–temperature–precipitation (TTP) diagrams
   - Machine learning features derived from experimental data

---

This hierarchy ensures that extracted data are **structured, interoperable, and context-rich**, capturing not only outcomes (e.g., corrosion rate) but also the causal processing–structure–property relationships essential for advancing DSS science and engineering. The inclusion of nitrogen content, phase balance quantification, and secondary phase identification is particularly critical, as these factors dominantly control the dual-phase synergy that defines DSS performance.

