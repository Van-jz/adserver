package com.leeyom.scaffold.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 设备信息DTO
 * 从 ifa_device.csv 文件中加载的设备数据
 *
 * @author Claude Code
 * @since 2025-11-30
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DeviceInfo {
    /**
     * IFA (Identifier for Advertising) - 广告标识符
     * 例如: dd501f6a-01f9-4342-ad73-732be8c6d99d
     */
    private String ifa;

    /**
     * 计数
     */
    private Integer count;

    /**
     * 操作系统
     * 例如: Android, iOS
     */
    private String os;

    /**
     * 操作系统版本
     * 例如: 14, 15
     */
    private String osv;

    /**
     * 设备型号
     * 例如: Moto G24 Power, iPhone 14 Pro
     */
    private String model;

    /**
     * 设备制造商
     * 例如: Motorola, Samsung, Apple
     */
    private String make;

    /**
     * 屏幕高度（像素）
     */
    private Integer h;

    /**
     * 屏幕宽度（像素）
     */
    private Integer w;
}
