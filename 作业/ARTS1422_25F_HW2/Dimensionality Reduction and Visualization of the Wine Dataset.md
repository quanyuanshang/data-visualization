# **Dimensionality Reduction and Visualization of the Wine Dataset**

### **1. Introduction**

In this project, we apply **Principal Component Analysis (PCA)**, **t-distributed Stochastic Neighbor Embedding (t-SNE)**, and **Uniform Manifold Approximation and Projection (UMAP)** to the **Wine dataset**.
 The goal is to project the data into two dimensions and visually compare how well each method separates different wine classes. We also create an **interactive visualization using D3.js**, where users can explore the 2D projections and identify class clusters interactively.

------

### **2. Dataset Description**

The dataset used in this project is the **Wine dataset** from the UCI Machine Learning Repository.
 It contains results of a chemical analysis of wines grown in the same region in Italy, but derived from three different cultivars.

| Property                 | Description                                                  |
| ------------------------ | ------------------------------------------------------------ |
| **Number of instances**  | 178                                                          |
| **Number of attributes** | 13 continuous features                                       |
| **Target classes**       | 3 (Cultivar 1, 2, and 3)                                     |
| **Feature examples**     | Alcohol, Malic acid, Ash, Magnesium, Flavanoids, Color intensity, Proline, etc. |

Each feature represents a quantitative measurement from a sample of wine, and the target label corresponds to the cultivar type.
 Before applying dimensionality reduction, all features were standardized using **z-score normalization** to ensure that features with large numeric ranges did not dominate the results.

------

### **3. Methodology**

#### **3.1 Data Preprocessing**

1. Loaded the Wine dataset from `sklearn.datasets.load_wine()`.
2. Standardized the data using `StandardScaler`.
3. Split the dataset into feature matrix `X` (13D) and target labels `y` (3 classes).

#### **3.2 Dimensionality Reduction Methods**

##### **(a) PCA**

Principal Component Analysis is a linear dimensionality reduction method that projects the data onto orthogonal axes capturing the maximum variance.
 We used `sklearn.decomposition.PCA(n_components=2)` to reduce the data to two principal components.
 PCA provides a fast and interpretable baseline visualization.

##### **(b) t-SNE**

t-SNE (t-distributed Stochastic Neighbor Embedding) is a nonlinear method designed to preserve local structure and reveal clusters in the data.
 It minimizes the Kullback-Leibler divergence between pairwise similarities in high and low dimensions.
 We used `sklearn.manifold.TSNE(n_components=2, perplexity=30, learning_rate=200, random_state=42)` for the projection.
 t-SNE often reveals well-separated clusters but is computationally intensive.

##### **(c) UMAP**

UMAP (Uniform Manifold Approximation and Projection) is another nonlinear method based on manifold learning and topological structures.
 It tends to preserve both local and global relationships better than t-SNE and is more efficient.
 We used `umap.UMAP(n_neighbors=20, min_dist=0.1, random_state=42)`.

#### **3.3 Visualization**

The reduced 2D coordinates from PCA, t-SNE, and UMAP were exported as CSV files and visualized using **D3.js** within a Vue-based web application.
 Each projection is displayed as an interactive scatter plot where:

- Each point represents a wine sample.
- Colors correspond to the three cultivars.
- Hovering highlights sample details.
- Lasso selection allows dynamic comparison across multiple panels.

------

### **4. Results and Evaluation**

#### **4.1 PCA Results**

- PCA’s first two components explain around **55–60%** of total variance.
- Some separation is visible, but overlap exists between Class 1 and Class 2.
- PCA performs well for linear separability but cannot capture nonlinear structures.

#### **4.2 t-SNE Results**

- t-SNE produces clear, compact clusters with minimal overlap.
- It effectively preserves local similarities and visually separates the three cultivars.
- However, global distances between clusters are not meaningful, and results depend on hyperparameters (especially *perplexity*).

#### **4.3 UMAP Results**

- UMAP achieves a balance between global and local structure preservation.
- Clusters are clearly separated, similar to t-SNE, but computation is faster and results are more stable.
- UMAP provides interpretable and reproducible embeddings with fewer hyperparameter sensitivities.

#### **4.4 Comparative Summary**

| Method    | Type      | Strengths                          | Weaknesses                         |
| --------- | --------- | ---------------------------------- | ---------------------------------- |
| **PCA**   | Linear    | Simple, interpretable, fast        | Fails on nonlinear data            |
| **t-SNE** | Nonlinear | Excellent local clustering         | Slow, non-global                   |
| **UMAP**  | Nonlinear | Preserves local & global structure | Requires tuning neighbors/min_dist |

------

### **5. Visualization Results**

![image-20251020232827161](C:\Users\ASUS\AppData\Roaming\Typora\typora-user-images\image-20251020232827161.png)

![image-20251020232948396| Hovering to view sample IDs and features.](C:\Users\ASUS\AppData\Roaming\Typora\typora-user-images\image-20251020232948396.png)

![image-20251020233005156|Lasso selection to highlight selected samples across all projections simultaneously.](C:\Users\ASUS\AppData\Roaming\Typora\typora-user-images\image-20251020233005156.png)

![image-20251020233025515| hovering while lasso selecting](C:\Users\ASUS\AppData\Roaming\Typora\typora-user-images\image-20251020233025515.png)

The figure shows samples colored by class:

- **PCA**: overlapping clusters.
- **t-SNE**: distinct compact clusters.
- **UMAP**: balanced separation with smooth transitions.

The D3-based interface allows:

- Hovering to view sample IDs and features.
- Lasso selection to highlight selected samples across all projections simultaneously.
- Side-by-side comparison of methods.

------

### **6. Conclusion**

This project demonstrated how different dimensionality reduction methods can reveal varying structures in the same dataset.

- **PCA** offers a fast and interpretable baseline.
- **t-SNE** excels in uncovering local clusters.
- **UMAP** provides a stable, efficient, and visually balanced representation.

The **interactive visualization** built using Vue and D3 enables intuitive exploration of these embeddings and facilitates better understanding of relationships within the dataset.
 Overall, UMAP and t-SNE outperform PCA in separating the wine classes, confirming the advantage of nonlinear approaches for complex datasets.

------

