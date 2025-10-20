<template>
  <div id="app" style="font-family: Arial; padding: 12px">
    <h2>Wine: PCA vs t-SNE vs UMAP (hover & lasso cross-highlighting)</h2>
    <div style="display: flex; gap: 20px">
      <scatter-panel
        v-for="panel in panels"
        :key="panel.id"
        :title="panel.title"
        :csvpath="panel.csv"
        :sharedSelection="selection"
        :sharedHoverIndex="hoverIndex"
        @update-selection="onUpdateSelection"
        @hover-index="onHoverIndex"
      />
    </div>
    <p>
      Tip: hover a point to highlight the same index across panels. Click-drag
      to draw a lasso (hold left mouse, release to finish).
    </p>
  </div>
</template>

<script>
import ScatterPanel from "./components/ScatterPanel.vue";

export default {
  name: "App",
  components: { ScatterPanel },
  data() {
    return {
      selection: new Set(), // global set of indices selected by lasso
      hoverIndex: null,
      panels: [
        { id: "pca", title: "PCA", csv: "/reduced_pca.csv" },
        { id: "tsne", title: "t-SNE", csv: "/reduced_tsne.csv" },
        { id: "umap", title: "UMAP", csv: "/reduced_umap.csv" },
      ],
    };
  },
  methods: {
    onUpdateSelection(indicesArr) {
      // receive array of indices and set globally
      this.selection = new Set(indicesArr);
      // emit down? we pass as prop so child watchers update
    },
    onHoverIndex(idxOrNull) {
      // forward hover index to all panels by updating a reactive property
      // we'll set a small reactive field so children receive prop change
      this.hoverIndex = idxOrNull;
    },
  },
};
</script>