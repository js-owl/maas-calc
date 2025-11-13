# Request/Response Flow Diagrams

This document contains comprehensive Mermaid diagrams showing the request/response flow and function call sequences for all endpoints in the Manufacturing Calculation API v3.3.0.

## 1. Overall Request/Response Flow

This high-level diagram shows the complete flow from client request to response:

```mermaid
graph TD
    A[Client Request] --> B[FastAPI Router]
    B --> C{Endpoint Type}
    
    C -->|/calculate-price| D[calculate_price Function]
    C -->|/materials| E[list_materials Function]
    C -->|/services| F[list_services Function]
    C -->|/coefficients| G[list_coefficients Function]
    C -->|/locations| H[list_locations Function]
    C -->|/health| I[health_check Function]
    C -->|/version| J[get_version Function]
    
    D --> K{File Upload?}
    K -->|Yes| L[ParameterExtractor]
    K -->|No| M[Use Provided Parameters]
    
    L --> N[File Analysis]
    N --> O[STL/STP Extractor]
    O --> P[Geometric Features]
    P --> Q[ML Features Available?]
    
    Q -->|Yes| R[ML Model Prediction]
    Q -->|No| S[Rule-Based Calculation]
    
    M --> T[Parameter Validation]
    T --> U[Apply Safeguards]
    U --> V[Calculation Router]
    
    R --> W[ML Calculator]
    S --> X[Rule-Based Calculator]
    V --> Y[Service Calculator]
    
    W --> Z[Price Calculation]
    X --> Z
    Y --> Z
    
    Z --> AA[Response Assembly]
    AA --> BB[UnifiedCalculationResponse]
    BB --> CC[Client Response]
    
    E --> DD[Constants Lookup]
    F --> DD
    G --> DD
    H --> DD
    I --> EE[Health Status]
    J --> FF[Version Info]
    
    DD --> GG[Configuration Response]
    EE --> GG
    FF --> GG
    GG --> CC
    
    style R fill:#e1f5fe
    style W fill:#e1f5fe
    style S fill:#fff3e0
    style X fill:#fff3e0
    style BB fill:#f3e5f5
```

## 2. Endpoint Overview

This diagram shows all available endpoints and their purposes:

```mermaid
graph LR
    A[Client] --> B[FastAPI Application]
    
    B --> C[Main Calculation Endpoint]
    B --> D[Configuration Endpoints]
    B --> E[System Endpoints]
    
    C --> C1["/calculate-price<br/>POST<br/>Unified manufacturing calculation"]
    
    D --> D1["/materials<br/>GET<br/>List available materials"]
    D --> D2["/services<br/>GET<br/>List manufacturing services"]
    D --> D3["/coefficients<br/>GET<br/>List tolerance/finish/cover options"]
    D --> D4["/locations<br/>GET<br/>List manufacturing locations"]
    
    E --> E1["/health<br/>GET<br/>Health check"]
    E --> E2["/version<br/>GET<br/>API version info"]
    E --> E3["/<br/>GET<br/>API information"]
    
    style C1 fill:#e8f5e8
    style D1 fill:#fff3e0
    style D2 fill:#fff3e0
    style D3 fill:#fff3e0
    style D4 fill:#fff3e0
    style E1 fill:#e3f2fd
    style E2 fill:#e3f2fd
    style E3 fill:#e3f2fd
```

## 3. Detailed Function Call Diagrams

### 3.1 3D Printing Service Flow

```mermaid
graph TD
    A[POST /calculate-price] --> B[calculate_price Function]
    B --> C[validate_calculation_request]
    C --> D{File Data Provided?}
    
    D -->|Yes| E[ParameterExtractor.extract_parameters_from_file]
    D -->|No| F[Use Request Parameters]
    
    E --> G[STLExtractor/STPExtractor]
    G --> H[File Analysis]
    H --> I[Extract Geometric Features]
    I --> J[ML Features Available?]
    
    J -->|Yes| K[MLPrintingCalculator]
    J -->|No| L[PrintingCalculator]
    
    F --> M[merge_parameters]
    M --> N[apply_safeguards]
    N --> O[should_use_ml]
    O -->|Yes| K
    O -->|No| L
    
    K --> P[MLPredictor.predict_from_file_features]
    P --> Q[XGBoost Model Prediction]
    Q --> R[Calculate Work Price]
    
    L --> S[calculate_printing_price]
    S --> T[calculate_mat_volume]
    S --> U[calculate_mat_weight]
    S --> V[calculate_mat_price]
    S --> W[calculate_work_price]
    S --> X[calculate_work_time]
    S --> Y[calculate_k_complexity]
    S --> Z[calculate_k_quantity]
    
    R --> AA[Apply Coefficients]
    Y --> AA
    Z --> AA
    AA --> BB[calculate_cost]
    BB --> CC[calculate_cycle]
    CC --> DD[Build Response]
    
    DD --> EE[UnifiedCalculationResponse]
    EE --> FF[ResponseWrapper.success_response]
    FF --> GG[Client Response]
    
    style K fill:#e1f5fe
    style P fill:#e1f5fe
    style Q fill:#e1f5fe
    style L fill:#fff3e0
    style S fill:#fff3e0
```

### 3.2 CNC Milling Service Flow

```mermaid
graph TD
    A[POST /calculate-price] --> B[calculate_price Function]
    B --> C[validate_calculation_request]
    C --> D{File Data Provided?}
    
    D -->|Yes| E[ParameterExtractor.extract_parameters_from_file]
    D -->|No| F[Use Request Parameters]
    
    E --> G[STLExtractor/STPExtractor]
    G --> H[File Analysis]
    H --> I[Extract Geometric Features]
    I --> J[ML Features Available?]
    
    J -->|Yes| K[MLCNCMillingCalculator]
    J -->|No| L[CNCMillingCalculator]
    
    F --> M[merge_parameters]
    M --> N[apply_safeguards]
    N --> O[should_use_ml]
    O -->|Yes| K
    O -->|No| L
    
    K --> P[MLPredictor.predict_from_file_features]
    P --> Q[XGBoost Model Prediction]
    Q --> R[Calculate Work Price]
    
    L --> S[calculate_cnc_milling_price]
    S --> T[calculate_mat_volume]
    S --> U[calculate_mat_weight]
    S --> V[calculate_mat_price]
    S --> W[calculate_work_price]
    S --> X[calculate_work_time]
    S --> Y[calculate_k_complexity]
    S --> Z[calculate_k_quantity]
    S --> AA[Select Suitable Machines]
    
    R --> BB[Apply Coefficients]
    Y --> BB
    Z --> BB
    BB --> CC[calculate_cost]
    CC --> DD[calculate_cycle]
    DD --> EE[Build Response]
    
    EE --> FF[UnifiedCalculationResponse]
    FF --> GG[ResponseWrapper.success_response]
    GG --> HH[Client Response]
    
    style K fill:#e1f5fe
    style P fill:#e1f5fe
    style Q fill:#e1f5fe
    style L fill:#fff3e0
    style S fill:#fff3e0
```

### 3.3 CNC Lathe Service Flow

```mermaid
graph TD
    A[POST /calculate-price] --> B[calculate_price Function]
    B --> C[validate_calculation_request]
    C --> D{File Data Provided?}
    
    D -->|Yes| E[ParameterExtractor.extract_parameters_from_file]
    D -->|No| F[Use Request Parameters]
    
    E --> G[STLExtractor/STPExtractor]
    G --> H[File Analysis]
    H --> I[Extract Geometric Features]
    I --> J[ML Features Available?]
    
    J -->|Yes| K[MLCNCLatheCalculator]
    J -->|No| L[CNCLatheCalculator]
    
    F --> M[merge_parameters]
    M --> N[apply_safeguards]
    N --> O[should_use_ml]
    O -->|Yes| K
    O -->|No| L
    
    K --> P[MLPredictor.predict_from_file_features]
    P --> Q[XGBoost Model Prediction]
    Q --> R[Calculate Work Price]
    
    L --> S[calculate_cnc_lathe_price]
    S --> T[calculate_mat_volume_cylindrical]
    S --> U[calculate_mat_weight]
    S --> V[calculate_mat_price]
    S --> W[calculate_work_price]
    S --> X[calculate_work_time]
    S --> Y[calculate_k_complexity]
    S --> Z[calculate_k_quantity]
    S --> AA[Select Suitable Lathe Machines]
    
    R --> BB[Apply Coefficients]
    Y --> BB
    Z --> BB
    BB --> CC[calculate_cost]
    CC --> DD[calculate_cycle]
    DD --> EE[Build Response]
    
    EE --> FF[UnifiedCalculationResponse]
    FF --> GG[ResponseWrapper.success_response]
    GG --> HH[Client Response]
    
    style K fill:#e1f5fe
    style P fill:#e1f5fe
    style Q fill:#e1f5fe
    style L fill:#fff3e0
    style S fill:#fff3e0
```

### 3.4 Painting Service Flow

```mermaid
graph TD
    A[POST /calculate-price] --> B[calculate_price Function]
    B --> C[validate_calculation_request]
    C --> D{File Data Provided?}
    
    D -->|Yes| E[ParameterExtractor.extract_parameters_from_file]
    D -->|No| F[Use Request Parameters]
    
    E --> G[STLExtractor/STPExtractor]
    G --> H[File Analysis]
    H --> I[Extract Geometric Features]
    I --> J[ML Features Available?]
    
    J -->|Yes| K[MLPaintingCalculator]
    J -->|No| L[PaintingCalculator]
    
    F --> M[merge_parameters]
    M --> N[apply_safeguards]
    N --> O[should_use_ml]
    O -->|Yes| K
    O -->|No| L
    
    K --> P[MLPredictor.predict_from_file_features]
    P --> Q[XGBoost Model Prediction]
    Q --> R[Calculate Work Price]
    
    L --> S[calculate_painting_price]
    S --> T[Calculate Paint Area]
    S --> U[calculate_mat_price]
    S --> V[calculate_work_price]
    S --> W[calculate_work_time]
    S --> X[calculate_k_complexity]
    S --> Y[calculate_k_quantity]
    S --> Z[Apply Paint Coefficients]
    
    R --> AA[Apply Coefficients]
    X --> AA
    Y --> AA
    AA --> BB[calculate_cost]
    BB --> CC[calculate_cycle]
    CC --> DD[Build Response]
    
    DD --> EE[UnifiedCalculationResponse]
    EE --> FF[ResponseWrapper.success_response]
    FF --> GG[Client Response]
    
    style K fill:#e1f5fe
    style P fill:#e1f5fe
    style Q fill:#e1f5fe
    style L fill:#fff3e0
    style S fill:#fff3e0
```
## 4. ML Model Integration Flow UPDATED

This detailed diagram shows how ML models are integrated into the calculation process with enhanced file extraction details:

```mermaid
graph TD
    A[UnifiedCalculationRequest] --> B[main.py<br>.post&#40/calculate-price&#41]
    B --> C[main.py<br>validation_errors]
    C --> D[utils.validation_utils.py<br>validate_calculation_request&#40;material_id, material_form, dimensions, quantity, tolerance_id, finish_id, cover_id, file_data, file_name, file_type&#41;]
    D --> AAA[main.py<br>validation_errors]
    AAA --> AAB[utils.validation_utils.py<br>create_validation_error_response<br>utils.response_utils.py<br>ResponseWrapper.error_response]

    AAA --> |Step 1: Extract parameters from file if provided| AAC[main.py<br>if request.file_data and request.file_name and request.file_type]
    AAC --> AAD[utils.parameter_extractor.py<br>extract_parameters_from_file]
    AAD --> E{File Type?}
    E -->|STL| F[STLExtractor]
    E -->|STP| G[STPExtractor]

    F --> H[extractors.stl_extractor.py]
    H --> I[extractors.file_extractor.py<br>_save_temp_file]
    I --> J[extractors.stl_extractor.py_analyze_stl_file]
    I --> K[volume, surface area]
    I --> L[features: face, vertex, edge counts]
    I --> M[ml‑compatible:<br>obb; min, mid, max sizes;<br>aspect_ratios; check_sizes_for_lathe]

    G --> O[extractors.stp_extractor.py]
    O --> P[extractors.file_extractor.py<br>_save_temp_file]
    P --> Q[min_obb and derives]
    P --> R[volume, surfaces and generals]
    P --> S[surface and edges features and its derives]

    K --> U[extractors.file_extractor.py<br>_cleanup_temp_file]
    L --> U
    M --> U
    Q --> U
    R --> U
    S --> U

    U --> V[main.py<br>if extracted_params.get&#40'volume'&#41<br>and extracted_params.get&#40'surface_area'&#41]
    V --> W[main.py<br>ml_features=extracted_params]

    W --> |Step 2: Merge extracted parameters with request parameters| WWA[utils.parameter_extractor.py<br>merge_parameters]
    WWA --> WWB[main.py<br>if ml_features]
    WWB --> WWD[main.py<br>merged_params&#91'ml_features'&#93=ml_features]

    WWD --> |Step 3: Apply safeguards for missing parameters| WWE[utils.safeguards.py<br>apply_safeguards]
    WWE --> WWF[apply defaults, dimensions, material_id, material_form]

    WWF --> |Step 4: Determine calculation method and route| WWG[utils.calculation_router.py<br>should_use_ml]
    WWG --> WWH[utils.calculation_router.py<br>if not ENABLE_ML_MODELS or not ml_predictor.is_model_available]
    WWG --> WWI[utils.calculation_router.py<br>if service_id not in &#91cnc-milling, cnc-lathe&#93]
    WWG --> WWJ[utils.calculation_router.py<br>if not ml_features]
    WWG --> WWK[utils.calculation_router.py<br>if not &#91'volume', 'surface_area'&#93 in ml_features]
    WWG --> WWL[utils.calculation_router.py<br>route_calculation]
    WWH --> WWM[rule‑based calculations]
    WWI --> WWM
    WWJ --> WWM
    WWK --> WWM

    WWL --> WWN[utils.calculation_router.py<br>_get_calculator]
    WWN --> WWO[calculators.ml_calculator.py<br>suitable_machines]
    WWO --> WWP[calculations.core.py<br>check_machines]
    WWP --> WWO
    WWO --> WWQ[calculators.ml_calculator.py<br>material_info]
    WWQ --> WWR[calculations.core.py<br>get_material_info]
    WWR --> WWQ
    WWQ --> WWS[calculators.ml_calculator.py<br>predicted_hours, is_need_special_equipment]
    WWS --> WWT[utils.ml_predictor.py<br>predict_from_file_features]

    WWT --> BB[utils.ml_predictor.py<br>extract_features_from_file<br>extract features and define zero material properties]

    BB --> CC[utils.ml_predictor.py<br>preprocess_features<br>update material info, map material_bar to russian,<br>define and transform categoricals, scaler features,<br>predict by clusterer and transform by reducer,<br>reindex by xgb regressor]

    CC --> HH[utils.ml_predictor.py<br>predict_work_time<br>predict by xgb regressor]
    HH --> II[utils.ml_predictor.py<br>predict_is_need_special_equipment<br>predict bool by xgb classifier]
    II --> JJ[calculators.ml_calculator.py<br>if predicted_hours is None or is_need_special_equipment is None]
    JJ --> KK[ValueError]
    JJ --> LL[calculators.ml_calculator.py<br>k_quantity]
    LL --> MM[calculations.core.py<br>calculate_k_quantity]
    MM --> LL
    LL --> NN[calculators.ml_calculator.py<br>k_cover]
    NN --> OO[calculations.core.py<br>calculate_cover_coefficient]
    OO --> NN
    NN --> PP[calculators.ml_calculator.py<br>_calculate_material_costs]
    PP --> QQ[calculators.ml_calculator.py<br>material_data]
    QQ --> RR[calculations.core.py<br>get_material_info]
    RR --> QQ
    QQ --> SS[calculators.ml_calculator.py<br>price_special_equipment, part_price, part_price_one]
    SS --> TT[calculations.core.py<br>calculate_cost]
    TT --> SS
    SS --> UU[calculators.ml_calculator.py<br>manufacturing_cycle]
    UU --> VV[calculations.core.py<br>calculate_cycle]
    VV --> UU
    UU --> WW[calculators.ml_calculator.py<br>_create_base_response<br>UnifiedCalculationResponse]
    WW --> |Step 5: Add file information and calculation engine info| AAAA[main.py<br>if request.file_name]
    AAAA --> BBBB[main.py<br>if extracted_params.get&#40'extracted_dimensions'&#41]
    BBBB --> CCCC[main.py<br>ResponseWrapper.success_response]
    CCCC --> DDDD[utils.response_utils.py<br>success_response]
    DDDD --> EEEE[utils.response_utils.py<br>if request_id]
    EEEE --> FFFF[utils.response_utils.py<br>if metadata]
    FFFF --> GGGG[utils.response_utils.py<br>response]
```

## 4. ML Model Integration Flow OLD

This detailed diagram shows how ML models are integrated into the calculation process with enhanced file extraction details:

```mermaid
graph TD
    A[File Upload] --> B[Base64 Decode]
    B --> C[Create Temporary File]
    C --> D[File Type Detection]
    
    D --> E{File Type?}
    E -->|STL| F[STLExtractor]
    E -->|STP| G[STPExtractor]
    
    F --> H[trimesh Analysis]
    H --> I[Extract STL Features]
    I --> J[Volume & Surface Area]
    I --> K[OBB Dimensions]
    I --> L[Face/Vertex/Edge Counts]
    I --> M[Watertight Check]
    I --> N[Surface Entropy]
    
    G --> O[CADQuery Analysis]
    O --> P[Extract STP Features]
    P --> Q[Precise Volume & Surface]
    P --> R[CAD Bounding Box]
    P --> S[CAD Topology Counts]
    P --> T[CAD Surface Entropy]
    
    J --> U[Feature Combination]
    K --> U
    L --> U
    M --> U
    N --> U
    Q --> U
    R --> U
    S --> U
    T --> U
    
    U --> V[Calculate Aspect Ratios]
    V --> W["obb_x/obb_y, obb_y/obb_z, obb_x/obb_z"]
    
    U --> X[Calculate Size Metrics]
    X --> Y["min, median, max dimensions"]
    
    U --> Z[Check Lathe Suitability]
    Z --> AA[Equal dimension check]
    
    W --> BB[MLPredictor.extract_features_from_file]
    Y --> BB
    AA --> BB
    U --> BB
    
    BB --> CC[Feature Preprocessing]
    CC --> DD[Update Material Information]
    DD --> EE[Create Feature DataFrame]
    EE --> FF[Apply One-Hot Encoding]
    FF --> GG[Reindex to Model Features]
    
    GG --> HH[MLPredictor.predict_work_time]
    HH --> II[XGBoost Model Prediction]
    II --> JJ{Prediction Success?}
    
    JJ -->|Yes| KK[Use ML Prediction]
    JJ -->|No| LL[Fallback to Rule-Based]
    
    KK --> MM[Calculate Work Price from ML Hours]
    LL --> NN[Rule-Based Calculation]
    
    MM --> OO[Apply Manufacturing Coefficients]
    NN --> OO
    OO --> PP[Final Price Calculation]
    
    PP --> QQ[Response with ML Metadata]
    QQ --> RR[Include Feature Details]
    RR --> SS[Include Prediction Confidence]
    
    style H fill:#e1f5fe
    style O fill:#e1f5fe
    style II fill:#e1f5fe
    style KK fill:#e1f5fe
    style LL fill:#fff3e0
    style NN fill:#fff3e0
    style QQ fill:#f3e5f5
```

## 5. Configuration Endpoints Flow

This diagram shows how configuration endpoints retrieve data:

```mermaid
graph TD
    A[Configuration Request] --> B{Endpoint Type}
    
    B -->|/materials| C[list_materials Function]
    B -->|/services| D[list_services Function]
    B -->|/coefficients| E[list_coefficients Function]
    B -->|/locations| F[list_locations Function]
    
    C --> G[MATERIALS from constants.py]
    D --> H[Hardcoded Service List]
    E --> I[TOLERANCE from constants.py]
    E --> J[FINISH from constants.py]
    E --> K[COVER from constants.py]
    F --> L[LOCATIONS from constants.py]
    
    G --> M[Filter by Process]
    M --> N[Format Material Data]
    N --> O[ResponseWrapper.success_response]
    
    H --> P[Format Service Data]
    P --> O
    
    I --> Q[Format Tolerance Data]
    J --> R[Format Finish Data]
    K --> S[Format Cover Data]
    Q --> T[Combine Coefficient Data]
    R --> T
    S --> T
    T --> O
    
    L --> U[Format Location Data]
    U --> O
    
    O --> V[Client Response]
    
    style G fill:#fff3e0
    style I fill:#fff3e0
    style J fill:#fff3e0
    style K fill:#fff3e0
    style L fill:#fff3e0
```

## 6. File Extraction Pipeline Flow

This detailed diagram shows the complete file extraction process for both STL and STP files:

```mermaid
graph TD
    A[Base64 File Upload] --> B[file_extractor._save_temp_file]
    B --> C[Decode Base64 Data]
    C --> D[Create Temporary File]
    D --> E[File Type Detection]
    
    E --> F{File Type?}
    F -->|STL| G[STLExtractor]
    F -->|STP/STEP| H[STPExtractor]
    
    G --> I[trimesh.load]
    I --> J[Extract Basic Geometry]
    J --> K[mesh.bounds]
    J --> L[mesh.volume]
    J --> M[mesh.area]
    
    K --> N[Calculate OBB Dimensions]
    N --> O["obb_x = max_x - min_x"]
    N --> P["obb_y = max_y - min_y"]
    N --> Q["obb_z = max_z - min_z"]
    
    L --> R[Calculate Derived Features]
    M --> R
    O --> R
    P --> R
    Q --> R
    
    R --> S[Calculate Aspect Ratios]
    S --> T["aspect_ratio_xy = obb_x/obb_y"]
    S --> U["aspect_ratio_yz = obb_y/obb_z"]
    S --> V["aspect_ratio_xz = obb_x/obb_z"]
    
    R --> W[Calculate Size Metrics]
    W --> X["min_size = min(obb_dims)"]
    W --> Y["mid_size = median(obb_dims)"]
    W --> Z["max_size = max(obb_dims)"]
    
    R --> AA[Calculate Bounding Box Volume]
    AA --> BB["bbox_volume = obb_x * obb_y * obb_z"]
    
    R --> CC[Check Lathe Suitability]
    CC --> DD["check_sizes_for_lathe = 1 if any dims equal"]
    
    I --> EE[Extract Surface Features]
    EE --> FF["mesh.faces count"]
    EE --> GG["mesh.vertices count"]
    EE --> HH["mesh.edges count"]
    EE --> II["mesh.is_watertight"]
    EE --> JJ["mesh.is_winding_consistent"]
    
    EE --> KK[Calculate Surface Entropy]
    KK --> LL["surface_entropy = log(face_count * surface_area)"]
    
    H --> MM["cadquery.importers.importStep"]
    MM --> NN{CADQuery Success?}
    NN -->|Yes| OO[Extract CAD Geometry]
    NN -->|No| PP[Basic STP Analysis Fallback]
    
    OO --> QQ["shape.val().BoundingBox"]
    QQ --> RR[Extract Bounds from CAD]
    RR --> SS["obb_x = bbox.xmax - bbox.xmin"]
    RR --> TT["obb_y = bbox.ymax - bbox.ymin"]
    RR --> UU["obb_z = bbox.zmax - bbox.zmin"]
    
    OO --> VV[Calculate Volume]
    VV --> WW{Volume Calculation Success?}
    WW -->|Yes| XX["volume = shape.val().Volume"]
    WW -->|No| YY["volume = obb_x * obb_y * obb_z"]
    
    OO --> ZZ[Calculate Surface Area]
    ZZ --> AAA{Surface Area Success?}
    AAA -->|Yes| BBB["surface_area = shape.val().Area"]
    AAA -->|No| CCC["surface_area = 2*(obb_x*obb_y + obb_y*obb_z + obb_x*obb_z)"]
    
    OO --> DDD[Extract CAD Topology]
    DDD --> EEE["shape.faces().objects count"]
    DDD --> FFF["shape.edges().objects count"]
    DDD --> GGG["shape.vertices().objects count"]
    
    DDD --> HHH[Calculate CAD Surface Entropy]
    HHH --> III["surface_entropy = log(face_count * surface_area)"]
    
    PP --> JJJ[Return Default Values]
    JJJ --> KKK["All features = 0 or default"]
    
    LL --> LLL[Combine All Features]
    III --> LLL
    KKK --> LLL
    
    LLL --> MMM[Create Feature Dictionary]
    MMM --> NNN[Return to ParameterExtractor]
    NNN --> OOO[Cleanup Temporary File]
    OOO --> PPP[Return Extracted Parameters]
    
    style I fill:#e1f5fe
    style MM fill:#e1f5fe
    style OO fill:#e1f5fe
    style PP fill:#fff3e0
    style JJJ fill:#fff3e0
    style LLL fill:#f3e5f5
```

## 7. STL vs STP Processing Comparison

This diagram shows the key differences between STL and STP processing:

```mermaid
graph LR
    A[File Upload] --> B{File Type}
    
    B -->|STL| C[STL Processing]
    B -->|STP| D[STP Processing]
    
    C --> E[trimesh Library]
    E --> F[Mesh Analysis]
    F --> G[Triangular Mesh]
    G --> H[Watertight Check]
    G --> I[Winding Consistency]
    G --> J[Face/Vertex/Edge Count]
    
    D --> K[CADQuery Library]
    K --> L[OpenCASCADE Backend]
    L --> M[CAD Geometry]
    M --> N[Precise Volume]
    M --> O[Exact Surface Area]
    M --> P[CAD Topology]
    
    H --> Q[Feature Extraction]
    I --> Q
    J --> Q
    N --> Q
    O --> Q
    P --> Q
    
    Q --> R[ML Features]
    R --> S[Volume & Surface Area]
    R --> T[OBB Dimensions]
    R --> U[Aspect Ratios]
    R --> V[Size Metrics]
    R --> W[Complexity Measures]
    R --> X[Lathe Suitability]
    
    S --> Y[ML Model Input]
    T --> Y
    U --> Y
    V --> Y
    W --> Y
    X --> Y
    
    style E fill:#e1f5fe
    style K fill:#e1f5fe
    style L fill:#e1f5fe
    style F fill:#fff3e0
    style M fill:#fff3e0
    style Y fill:#f3e5f5
```

## 8. Error Handling Flow

This diagram shows how errors are handled throughout the system:

```mermaid
graph TD
    A[Request Processing] --> B{Validation Error?}
    B -->|Yes| C[create_validation_error_response]
    B -->|No| D[File Processing]
    
    D --> E{File Processing Error?}
    E -->|Yes| F[File Processing Error Response]
    E -->|No| G[Parameter Extraction]
    
    G --> H{Extraction Error?}
    H -->|Yes| I[Extraction Error Response]
    H -->|No| J[Calculation]
    
    J --> K{Calculation Error?}
    K -->|Yes| L[Calculation Error Response]
    K -->|No| M[ML Prediction]
    
    M --> N{ML Error?}
    N -->|Yes| O[Fallback to Rule-Based]
    N -->|No| P[Use ML Result]
    
    O --> Q{Rule-Based Error?}
    Q -->|Yes| R[Rule-Based Error Response]
    Q -->|No| S[Success Response]
    
    P --> S
    
    C --> T[Error Response]
    F --> T
    I --> T
    L --> T
    R --> T
    S --> U[Success Response]
    
    T --> V[Client]
    U --> V
    
    style C fill:#ffebee
    style F fill:#ffebee
    style I fill:#ffebee
    style L fill:#ffebee
    style R fill:#ffebee
    style O fill:#fff3e0
    style S fill:#e8f5e8
    style U fill:#e8f5e8
```

## Key Function Call Patterns

### Main Calculation Flow
1. **Entry**: `main.py:calculate_price()`
2. **Validation**: `validation_utils:validate_calculation_request()`
3. **File Processing**: `parameter_extractor:extract_parameters_from_file()`
4. **Safeguards**: `safeguards:apply_safeguards()`
5. **Routing**: `calculation_router:route_calculation()`
6. **Calculation**: Service-specific calculator
7. **Response**: `response_utils:ResponseWrapper.success_response()`

### ML Integration Flow
1. **Feature Extraction**: `extractors:STLExtractor/STPExtractor`
2. **ML Processing**: `ml_predictor:extract_features_from_file()`
3. **Preprocessing**: `ml_predictor:preprocess_features()`
4. **Prediction**: `ml_predictor:predict_work_time()`
5. **Fallback**: Automatic fallback to rule-based on failure

### Configuration Flow
1. **Request**: Configuration endpoint
2. **Data Lookup**: Constants from `constants.py`
3. **Formatting**: Service-specific formatting
4. **Response**: `ResponseWrapper.success_response()`

## 9. Technical Implementation Details

### STL Processing Technical Details
- **Library**: `trimesh` - Python library for 3D mesh processing
- **File Format**: STL (STereoLithography) - triangular mesh representation
- **Key Operations**:
  - `mesh.bounds` - Get axis-aligned bounding box
  - `mesh.volume` - Calculate mesh volume using divergence theorem
  - `mesh.area` - Calculate surface area from triangle faces
  - `mesh.is_watertight` - Check if mesh forms closed surface
  - `mesh.is_winding_consistent` - Check normal vector consistency
- **Performance**: Optimized for large meshes, memory-efficient processing
- **Limitations**: Approximate volume calculation, no parametric geometry

### STP Processing Technical Details
- **Library**: `CADQuery` with `OpenCASCADE` backend
- **File Format**: STEP (Standard for Exchange of Product Data) - parametric CAD
- **Key Operations**:
  - `cq.importers.importStep()` - Load STEP file with full geometric fidelity
  - `shape.val().BoundingBox()` - Get precise CAD bounding box
  - `shape.val().Volume()` - Calculate exact volume from CAD geometry
  - `shape.val().Area()` - Calculate exact surface area
  - `shape.faces().objects` - Access CAD topology
- **Performance**: Handles complex assemblies, parametric models
- **Advantages**: Precise calculations, full geometric fidelity

### ML Feature Engineering
- **Geometric Features**: Volume, surface area, OBB dimensions
- **Shape Features**: Aspect ratios, size metrics, compactness
- **Complexity Features**: Face count, vertex count, surface entropy
- **Manufacturing Features**: Lathe suitability, material compatibility
- **Preprocessing**: One-hot encoding for categorical features
- **Model Input**: 50+ features for XGBoost prediction

### Error Handling Strategy
- **File Processing**: Graceful fallback with default values
- **ML Prediction**: Automatic fallback to rule-based calculation
- **CAD Analysis**: Multi-level fallback (CADQuery → basic → defaults)
- **Validation**: Comprehensive parameter validation and safeguards

### Performance Characteristics
- **STL Processing**: < 2 seconds for typical files
- **STP Processing**: < 3 seconds for complex CAD files
- **ML Prediction**: < 100ms for work time estimation
- **Memory Usage**: Optimized for large file processing
- **Concurrent Processing**: Supports multiple simultaneous requests

## 10. STL ML Feature Extraction Process Flow

This detailed diagram shows the exact step-by-step process of extracting ML features from STL files, including all calculations, transformations, and data structures.

```mermaid
flowchart TD
    A[Base64 STL File] --> B[Decode Base64]
    B --> C[Save Temporary File]
    C --> D[trimesh.load]
    
    D --> E[Mesh Object]
    E --> F[Extract Basic Geometry]
    
    F --> G[mesh.bounds]
    F --> H[mesh.volume]
    F --> I[mesh.area]
    
    G --> J[Calculate OBB Dimensions]
    J --> K["obb_x = max_bounds[0] - min_bounds[0]"]
    J --> L["obb_y = max_bounds[1] - min_bounds[1]"]
    J --> M["obb_z = max_bounds[2] - min_bounds[2]"]
    
    K --> N[Calculate Size Metrics]
    L --> N
    M --> N
    N --> O["min_size = min of dimensions"]
    N --> P["mid_size = median of dimensions"]
    N --> Q["max_size = max of dimensions"]
    
    K --> R[Calculate Aspect Ratios]
    L --> R
    M --> R
    R --> S["aspect_ratio_xy = obb_x / obb_y"]
    R --> T["aspect_ratio_yz = obb_y / obb_z"]
    R --> U["aspect_ratio_xz = obb_x / obb_z"]
    
    K --> V[Calculate Bounding Box Volume]
    L --> V
    M --> V
    V --> W["bbox_volume = obb_x × obb_y × obb_z"]
    
    K --> X[Check Lathe Suitability]
    L --> X
    M --> X
    X --> Y["check_sizes_for_lathe = equal dims check"]
    
    E --> Z[Extract Surface Features]
    Z --> AA["mesh.faces count"]
    Z --> BB["mesh.vertices count"]
    Z --> CC["mesh.edges count"]
    Z --> DD["mesh.is_watertight"]
    Z --> EE["mesh.is_winding_consistent"]
    
    AA --> FF[Calculate Surface Entropy]
    I --> FF
    FF --> GG["surface_entropy = log calculation"]
    
    K --> HH[ML Predictor Processing]
    L --> HH
    M --> HH
    O --> HH
    P --> HH
    Q --> HH
    S --> HH
    T --> HH
    U --> HH
    W --> HH
    Y --> HH
    AA --> HH
    BB --> HH
    CC --> HH
    DD --> HH
    EE --> HH
    GG --> HH
    
    HH --> II[Add Material Properties]
    II --> JJ[Create Feature Dictionary]
    JJ --> KK[50+ ML Features Ready]
    KK --> LL[One-Hot Encoding]
    LL --> MM[XGBoost Prediction Input]
    
    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style KK fill:#e8f5e8
    style MM fill:#fff3e0
```

### STL Feature Extraction Technical Details

#### 1. File Input Processing
- **Input**: Base64 encoded STL file string
- **Process**: `base64.b64decode(file_data)` → binary data
- **Output**: Temporary file saved to disk

#### 2. Trimesh Mesh Loading
- **Function**: `trimesh.load(str(file_path))`
- **Creates**: Mesh object with vertices, faces, and edges
- **Properties**: Geometric properties automatically calculated

#### 3. Basic Geometry Extraction
```python
# Extract bounding box coordinates
bounds = mesh.bounds  # Returns [[x_min, y_min, z_min], [x_max, y_max, z_max]]
min_bounds = bounds[0]
max_bounds = bounds[1]

# Extract volume and surface area
volume = mesh.volume  # Calculated using divergence theorem
surface_area = mesh.area  # Sum of all triangle face areas
```

#### 4. OBB (Oriented Bounding Box) Calculations
```python
# Calculate OBB dimensions
obb_x = max_bounds[0] - min_bounds[0]  # Length
obb_y = max_bounds[1] - min_bounds[1]  # Width  
obb_z = max_bounds[2] - min_bounds[2]  # Height
```

#### 5. Size Metrics Calculations
```python
# Calculate size statistics
obb_dims = [obb_x, obb_y, obb_z]
min_size = min(obb_dims)           # Smallest dimension
mid_size = np.median(obb_dims)     # Median dimension
max_size = max(obb_dims)           # Largest dimension
```

#### 6. Aspect Ratios Calculations
```python
# Calculate aspect ratios with zero-division protection
aspect_ratio_xy = obb_x / obb_y if obb_y > 0 else 1.0
aspect_ratio_yz = obb_y / obb_z if obb_z > 0 else 1.0
aspect_ratio_xz = obb_x / obb_z if obb_z > 0 else 1.0
```

#### 7. Bounding Box Volume
```python
# Calculate bounding box volume
bbox_volume = obb_x * obb_y * obb_z
```

#### 8. Lathe Suitability Check
```python
# Check if any two dimensions are equal (within tolerance)
check_sizes_for_lathe = 1 if any(
    abs(obb_dims[i] - obb_dims[j]) < 0.001 
    for i in range(3) for j in range(i+1, 3)
) else 0
```

#### 9. Surface Features Extraction
```python
# Extract mesh topology and quality features
features = {
    'face_count': len(mesh.faces),                    # Number of triangular faces
    'vertex_count': len(mesh.vertices),               # Number of vertices
    'edge_count': len(mesh.edges),                    # Number of edges
    'is_watertight': mesh.is_watertight,              # Closed surface check
    'is_winding_consistent': mesh.is_winding_consistent,  # Normal consistency
    'surface_entropy': math.log(face_count * surface_area)  # Complexity metric
}
```

#### 10. ML Feature Dictionary Assembly
The final feature dictionary contains 50+ features organized into categories:

**Geometric Features (15 features)**:
- `volume`, `surface_area`, `obb_x`, `obb_y`, `obb_z`
- `min_size`, `mid_size`, `max_size`
- `aspect_ratio_xy`, `aspect_ratio_yz`, `aspect_ratio_xz`
- `bbox_volume`, `check_sizes_for_lathe`

**Surface Features (6 features)**:
- `num_faces`, `num_edges`, `num_vertices`
- `surface_entropy`, `is_watertight`, `is_winding_consistent`

**Material Features (5 features)**:
- `material_bar`, `material_name`, `material_name_main`
- `material_group`, `material_coef`

**File Features (2 features)**:
- `filename`, `file_type`

**Additional Features (25+ features)**:
- Service-specific parameters
- Manufacturing coefficients
- Quality control parameters
- Process-specific features

#### 11. Data Flow Summary
1. **Base64 STL** → **Binary File** → **Trimesh Mesh**
2. **Mesh Object** → **Geometric Properties** → **Calculated Features**
3. **Raw Features** → **ML Predictor** → **Processed Features**
4. **Feature Dictionary** → **One-Hot Encoding** → **XGBoost Input**

#### 12. Error Handling
- **File Loading Errors**: Returns default values (0.0 for dimensions, False for booleans)
- **Calculation Errors**: Zero-division protection, fallback values
- **Mesh Analysis Errors**: Graceful degradation with warning logs
- **Feature Extraction Errors**: Returns None, triggers rule-based fallback

#### 13. Performance Characteristics
- **File Size**: Handles STL files up to 100MB efficiently
- **Processing Time**: < 2 seconds for typical files
- **Memory Usage**: Optimized for large meshes
- **Feature Count**: 50+ features extracted per file

This comprehensive process ensures that STL files are thoroughly analyzed to extract all relevant geometric, topological, and manufacturing features needed for accurate ML-based work time prediction.

These diagrams provide a comprehensive view of how requests flow through the system, how different services are processed, and how ML integration works alongside traditional rule-based calculations.
