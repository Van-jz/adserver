  /
  ├── ssp/
  │   └── POST req - SSP竞价请求入口，模拟向下游DSP发送竞价请求
  │
  ├── test/rtb/ (测试环境)
  │   ├── GET  change/interval/{interval} - 动态修改竞价频率控制参数
  │   ├── POST getAd - 接收OpenRTB竞价请求，返回广告响应（测试）
  │   ├── notice/
  │   │   ├── ANY  won - 竞价胜出通知回调
  │   │   ├── ANY  lose - 竞价失败通知回调
  │   │   └── ANY  bid - 竞价通知回调，返回广告物料ADM
  │   └── track/
  │       ├── ANY  startPlay - 广告开始播放事件跟踪
  │       ├── ANY  completePlay - 广告播放完成事件跟踪
  │       └── ANY  click - 广告点击事件跟踪
  │
  ├── prod/rtb/ (生产环境)
  │   ├── GET  change/interval/{interval} - 动态修改竞价频率控制参数
  │   ├── GET  change/maxPrice/{maxPrice} - 动态修改最高竞价上限
  │   ├── GET  change/maxMultiple/{maxMultiple} - 动态修改竞价倍数上限
  │   ├── GET  setSpendingLimit/{price} - 设置每日消费限额
  │   ├── GET  setWonPrice/{price} - 手动设置当日已消费金额
  │   ├── GET  wonPrice - 查询当日已消费金额
  │   ├── POST getAd - 接收OpenRTB竞价请求，返回广告响应（生产）
  │   ├── GET  adCost/{day} - 查询指定日期的广告成本总计
  │   ├── GET  guid/{day} - 查询指定日期的用户GUID统计
  │   ├── notice/
  │   │   ├── ANY  won - 竞价胜出通知回调，记录成本并触发限额策略
  │   │   ├── ANY  lose - 竞价失败通知回调
  │   │   └── ANY  bid - 竞价通知回调，返回广告物料ADM
  │   └── track/
  │       ├── ANY  startPlay - 广告开始播放事件跟踪
  │       ├── ANY  completePlay - 广告播放完成事件跟踪
  │       └── ANY  click - 广告点击事件跟踪
  │
  └── dev/rtb/ (开发工具)
      ├── GET  change/interval/{interval} - 动态修改竞价频率控制参数
      ├── POST upload/log/{day} - 手动上传指定日期的日志到OSS
      ├── GET  analysisLog/{startDay}/{endDay} - 分析指定日期范围的OSS日志
      └── GET  countBidResp/{day} - 统计指定日期的竞价响应数量

  核心流程说明：
  - /ssp/req - SSP入口，模拟向DSP发送竞价请求
  - /test|prod/rtb/getAd - DSP入口，接收竞价请求并返回广告
  - /test|prod/rtb/notice/* - OpenRTB回调通知（win/lose/bid）
  - /test|prod/rtb/track/* - 广告事件跟踪（播放/完成/点击）
  - /prod/rtb/change/* - 生产环境动态参数调整
  - /dev/rtb/* - 开发调试工具（日志管理、数据分析）
