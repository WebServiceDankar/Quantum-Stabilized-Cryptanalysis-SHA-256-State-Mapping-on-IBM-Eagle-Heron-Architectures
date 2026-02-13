import cupy as cp
print(f"CuPy {cp.__version__}")
try:
    k = cp.RawKernel(r'''
extern "C" __global__ void test_kernel(float* x) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    x[idx] = 42.0f;
}
''', 'test_kernel')
    x = cp.zeros(256, dtype=cp.float32)
    k((1,), (256,), (x,))
    cp.cuda.stream.get_current_stream().synchronize()
    print(f"Result: {x[0]}")
    print("GPU KERNEL COMPILATION: SUCCESS!")
except Exception as e:
    print(f"ERROR: {e}")
