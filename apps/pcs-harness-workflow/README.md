# PCS-Harness Workflow

独立的实时闭环可视化页面。它不包含离线回放或预置成功结果：浏览器提交已验证的 `ota_core` 网表后，后端启动一个全新运行目录，实时展示 Agent、GRPO、版图、DRC/LVS/PEX、后仿和 PVT 证据。

## 录制前置条件

- 已生成并冻结 `boundary_scan/selection.json`；
- Harness Python 位于 `/home/qlf/anaconda3/envs/Harness/bin/python`；
- PCS 隔离工作树和本地 Sky130A PDK 路径可用；
- `pnpm install` 已在本目录完成。

## 启动

```bash
./apps/pcs-harness-workflow/scripts/start-recording-demo.sh \
  --run-root /home/qlf/IOT/generated/analog_harness/ota_core_grpo_demo_20260826/recording_run \
  --selection /home/qlf/IOT/generated/analog_harness/ota_core_grpo_demo_20260826/boundary_scan/selection.json
```

页面地址为 `http://127.0.0.1:3103/`，API 为 `http://127.0.0.1:8103/`。启动服务不会自动运行电路；只有网页完成类型选择、网表上传、解析和预检并点击开始后，才创建新的 run。

成功状态只由真实 `L6_post_layout_pvt`、通过的性能合同及对应持久化证据产生。Agent 停止、运行预算耗尽、环境不满足或未达到 L6 都以失败结束，不切换到备用结果。
