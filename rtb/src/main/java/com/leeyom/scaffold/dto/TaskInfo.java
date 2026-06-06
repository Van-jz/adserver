package com.leeyom.scaffold.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 任务信息DTO
 *
 * @author Claude Code
 * @since 2025-11-15
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TaskInfo {
    /**
     * 目标元素
     * 取值: main_activity, navigate_interstitial, click_load, click_show, click_ad 等
     */
    private String targetElement;

    /**
     * 参数
     * - 当 targetElement 为 "click_load" 时: {"repeat":5, "inner_delay":2000} (整数类型)
     * - 其他情况: {} (空对象)
     */
    private Map<String, Object> params;

    /**
     * 目标页面
     * 目前取值为 null
     */
    private String targetPage;

    /**
     * 延迟时间（毫秒）
     * 代表停留多少ms后执行当前targetElement动作
     */
    private Integer delay;
}
