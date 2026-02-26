import torch
import torch.backends.cudnn as cudnn


def check_cuda_and_cudnn():
    print("=" * 30)
    print("CUDA & cuDNN 安装测试")
    print("=" * 30)

    # 1. 检查 CUDA 是否可用
    cuda_available = torch.cuda.is_available()
    print(f"1. CUDA 可用性: {cuda_available}")

    if not cuda_available:
        print("   [错误] 未检测到 CUDA，请检查驱动或 Toolkit 安装。")
        return

    # 2. 获取版本信息
    print(f"2. CUDA 版本: {torch.version.cuda}")
    print(f"3. cuDNN 版本: {cudnn.version()}")
    print(f"4. 当前 GPU 设备: {torch.cuda.get_device_name(0)}")

    # 3. cuDNN 状态检查
    print(f"5. cuDNN 是否可用: {cudnn.is_acceptable(torch.tensor(1.0).cuda())}")

    # 4. 实际运算测试 (进行一次矩阵乘法)
    print("\n[正在进行矩阵运算测试...]")
    try:
        # 创建两个随机矩阵并移至 GPU
        a = torch.randn(1000, 1000).to('cuda')
        b = torch.randn(1000, 1000).to('cuda')

        # 矩阵乘法 (会触发 cuDNN 优化)
        c = torch.matmul(a, b)

        print("6. 矩阵运算成功！GPU 和 cuDNN 工作正常。")
    except Exception as e:
        print(f"   [错误] 运算过程中出错: {e}")


if __name__ == "__main__":
    check_cuda_and_cudnn()