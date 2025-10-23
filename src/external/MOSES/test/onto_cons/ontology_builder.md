# 测试结果
文献：src/external/MOSES/data/processed_text/Baruwa2025 _ Mater. Res. Express _ Characteristics and properties of hot-deformed duplex stainless steel 2205 an overview.json
共34chunks
## qwen2.5-max
- 1M tokens——30chunks——1200s
## qwen3-max
- 1M tokens——22chunks——1200s
- 2M In-0.8M Out tokens——34chunks——15min——32元
## qwen3-next-80b-a3b-thinking
- 1M tokens——0chunks——880s
- 2M In-9M Out tokens——34chunks——122min
## qwen3-235b-a22b-thinking-2507
- 1M tokens——1chunks——1600s（大量chunk被中断）
- 2M In-6M Out tokens——34chunks——78min
## gpt-4.1
- 34chunks——13min——7$
## gpt-5
- 2M In-6M Out tokens——34chunks——78min

