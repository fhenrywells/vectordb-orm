from abc import ABC, abstractmethod
from vectordb_orm.similarity import FloatSimilarityMetric, BinarySimilarityMetric

class IndexBase(ABC):
    """
    Specify indexes used for embedding creation: https://milvus.io/docs/index.md
    Individual docstrings for the index types are taken from this page of ideal scenarios.

    """
    index_type: str

    def __init__(
        self,
        metric_type: FloatSimilarityMetric | BinarySimilarityMetric | None = None,
    ):
        # Choose a reasonable default if metric_type is null, depending on the type of index
        if metric_type is None:
            if isinstance(self, tuple(FLOATING_INDEXES)):
                metric_type = FloatSimilarityMetric.L2
            elif isinstance(self, tuple(BINARY_INDEXES)):
                metric_type = BinarySimilarityMetric.JACCARD

        self._assert_metric_type(metric_type)
        self.metric_type = metric_type

    @abstractmethod
    def get_index_parameters(self):
        pass

    @abstractmethod
    def get_inference_parameters(self):
        """
        NOTE: For simplicity, each index type will have the same inference parameters as index parameters. Milvus does allow
        for the customization of these per-query, but we will see how this use-case develops.
        """
        pass

    def _assert_metric_type(self, metric_type: FloatSimilarityMetric | BinarySimilarityMetric):
        """
        Binary indexes only support binary metrics, and floating indexes only support floating metrics. Assert
        that the combination of metric type and index is valid.

        """
        # Only support valid combinations of metric type and index
        if isinstance(metric_type, FloatSimilarityMetric):
            if not isinstance(self, tuple(FLOATING_INDEXES)):
                raise ValueError(f"Index type {self} is not supported for metric type {metric_type}")
        elif isinstance(metric_type, BinarySimilarityMetric):
            if not isinstance (self, tuple(BINARY_INDEXES)):
                raise ValueError(f"Index type {self} is not supported for metric type {metric_type}")


class FLAT(IndexBase):
    """
    - Relatively small dataset
    - Requires a 100% recall rate
    """
    index_type = "FLAT"

    def get_index_parameters(self):
        return {}

    def get_inference_parameters(self):
        return {"metric_type": self.metric_type.name}


class IVF_FLAT(IndexBase):
    """
    - High-speed query
    - Requires a recall rate as high as possible
    """
    index_type = "IVF_FLAT"

    def __init__(
        self,
        cluster_units: int,
        inference_comparison: int | None = None,
        metric_type: FloatSimilarityMetric | BinarySimilarityMetric | None = None,
    ):
        """
        :param cluster_units: Number of clusters (nlist in the docs)
        :param inference_comparison: Number of cluster centroids to compare during inference (nprobe in the docs)
            By default if this is not specified, it will be set to the same value as cluster_units.
        """
        super().__init__(metric_type=metric_type)

        if not (cluster_units >= 1 and cluster_units <= 65536):
            raise ValueError("cluster_units must be between 1 and 65536")
        if inference_comparison is not None and not (inference_comparison >= 1 and inference_comparison <= cluster_units):
            raise ValueError("inference_comparison must be between 1 and cluster_units")
        self.nlist = cluster_units
        self.nprobe = inference_comparison or cluster_units

    def get_index_parameters(self):
        return {"nlist": self.nlist}

    def get_inference_parameters(self):
        return {"nprobe": self.nprobe}


class IVF_SQ8(IndexBase):
    """
    - High-speed query
    - Limited memory resources
    - Accepts minor compromise in recall rate
    """
    index_type = "IVF_SQ8"

    def __init__(
        self,
        cluster_units: int,
        inference_comparison: int | None = None,
        metric_type: FloatSimilarityMetric | BinarySimilarityMetric | None = None,
    ):
        """
        :param cluster_units: Number of clusters (nlist in the docs)
        :param inference_comparison: Number of cluster centroids to compare during inference (nprobe in the docs)
            By default if this is not specified, it will be set to the same value as cluster_units.
        """
        super().__init__(metric_type=metric_type)

        if not (cluster_units >= 1 and cluster_units <= 65536):
            raise ValueError("cluster_units must be between 1 and 65536")
        if inference_comparison is not None and not (inference_comparison >= 1 and inference_comparison <= cluster_units):
            raise ValueError("inference_comparison must be between 1 and cluster_units")
        self.nlist = cluster_units
        self.nprobe = inference_comparison or cluster_units

    def get_index_parameters(self):
        return {"nlist": self.nlist}

    def get_inference_parameters(self):
        return {"nprobe": self.nprobe}


class IVF_PQ(IndexBase):
    """
    - Very high-speed query
    - Limited memory resources
    - Accepts substantial compromise in recall rate
    """
    index_type = "IVF_PQ"

    def __init__(
        self,
        cluster_units: int,
        product_quantization: int | None = None,
        inference_comparison: int | None = None,
        low_dimension_bits: int | None = None,
        metric_type: FloatSimilarityMetric | BinarySimilarityMetric | None = None,
    ):
        """
        :param cluster_units: Number of clusters (nlist in the docs)
        :param inference_comparison: Number of cluster centroids to compare during inference (nprobe in the docs)
            By default if this is not specified, it will be set to the same value as cluster_units.
        """
        super().__init__(metric_type=metric_type)

        if not (cluster_units >= 1 and cluster_units <= 65536):
            raise ValueError("cluster_units must be between 1 and 65536")
        if inference_comparison is not None and not (inference_comparison >= 1 and inference_comparison <= cluster_units):
            raise ValueError("inference_comparison must be between 1 and cluster_units")
        if low_dimension_bits is not None and not (low_dimension_bits >= 1 and low_dimension_bits <= 16):
            raise ValueError("low_dimension_bits must be between 1 and 16")
        self.m = product_quantization
        self.nbits = low_dimension_bits or 8
        self.nlist = cluster_units
        self.nprobe = inference_comparison or cluster_units

    def get_index_parameters(self):
        return {"nlist": self.nlist, "m": self.m, "nbits": self.nbits}

    def get_inference_parameters(self):
        return {"nprobe": self.nprobe}


class HNSW(IndexBase):
    """
    - High-speed query
    - Requires a recall rate as high as possible
    - Large memory resources
    """
    index_type = "HNSW"

    def __init__(
        self,
        max_degree: int,
        search_scope_index: int,
        search_scope_inference: int,
        metric_type: FloatSimilarityMetric | BinarySimilarityMetric | None = None,
    ):
        """
        :param max_degree: Maximum degree of the node
        :param search_scope: Search scope
        """
        super().__init__(metric_type=metric_type)

        if not (max_degree >= 4 and max_degree <= 64):
            raise ValueError("max_degree must be between 4 and 64")
        if not (search_scope_index >= 8 and search_scope_index <= 512):
            raise ValueError("search_scope must be between 1 and 512")
        if not (search_scope_inference >= 1 and search_scope_inference <= 32768):
            # NOTE: Technically this needs to be between [top_k, 32768], but we don't know what top_k is
            # at index time
            raise ValueError("search_scope must be between 1 and 32768")
        self.m = max_degree
        self.efConstruction = search_scope_index
        self.ef = search_scope_inference

    def get_index_parameters(self):
        return {"M": self.m, "efConstruction": self.efConstruction}

    def get_inference_parameters(self):
        return {"ef": self.ef}


class BIN_FLAT(IndexBase):
    """
    - Relatively small dataset
    - Requires a 100% recall rate
    """
    index_type = "BIN_FLAT"

    def get_index_parameters(self):
        return {}

    def get_inference_parameters(self):
        return {"metric_type": self.metric_type.name}


class BIN_IVF_FLAT(IndexBase):
    """
    - High-speed query
    - Requires a recall rate as high as possible
    """
    index_type = "BIN_IVF_FLAT"

    def __init__(
        self,
        cluster_units: int,
        inference_comparison: int | None = None,
        metric_type: FloatSimilarityMetric | BinarySimilarityMetric | None = None,
    ):
        """
        :param cluster_units: Number of clusters (nlist in the docs)
        :param inference_comparison: Number of cluster centroids to compare during inference (nprobe in the docs)
            By default if this is not specified, it will be set to the same value as cluster_units.
        """
        super().__init__(metric_type=metric_type)

        if not (cluster_units >= 1 and cluster_units <= 65536):
            raise ValueError("cluster_units must be between 1 and 65536")
        if inference_comparison is not None and not (inference_comparison >= 1 and inference_comparison <= cluster_units):
            raise ValueError("inference_comparison must be between 1 and cluster_units")
        self.nlist = cluster_units
        self.nprobe = inference_comparison or cluster_units

    def get_index_parameters(self):
        return {"nlist": self.nlist}

    def get_inference_parameters(self):
        return {"nprobe": self.nprobe}


FLOATING_INDEXES : set[IndexBase] = {FLAT, IVF_FLAT, IVF_SQ8, IVF_PQ, HNSW}
BINARY_INDEXES : set[IndexBase] = {BIN_FLAT, BIN_IVF_FLAT}
