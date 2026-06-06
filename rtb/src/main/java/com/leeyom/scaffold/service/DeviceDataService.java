package com.leeyom.scaffold.service;

import com.leeyom.scaffold.dto.DeviceInfo;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * 设备数据服务
 * 负责在应用启动时从 ifa_device.csv 文件加载设备数据到内存
 *
 * @author Claude Code
 * @since 2025-11-30
 */
@Service
@Slf4j
public class DeviceDataService {

    /**
     * 存储所有设备数据的内存列表
     */
    private final List<DeviceInfo> deviceList = new ArrayList<>();

    /**
     * 设备索引 HashMap
     * Key: "os/ver/model/brand" (全部小写)
     * Value: DeviceGroup 包含该类型设备的所有 GAID 列表
     */
    private final Map<String, DeviceGroup> deviceIndexMap = new HashMap<>();

    /**
     * specialDevice GAID 集合（os=Android && osv!=12），用于 O(1) 查询
     */
    private final Set<String> specialDeviceGaidSet = new HashSet<>();

    /**
     * 随机数生成器
     */
    private final Random random = new Random();

    /**
     * CSV 文件路径 (相对于应用启动目录)
     */
    private static final String CSV_FILE_PATH = "ifa_device.csv";

    /**
     * 应用启动时自动加载 CSV 文件
     */
    @PostConstruct
    public void init() {
        loadDeviceData();
    }

    /**
     * 从 CSV 文件加载设备数据到内存
     */
    private void loadDeviceData() {
        File csvFile = new File(CSV_FILE_PATH);

        if (!csvFile.exists()) {
            log.warn("设备数据文件不存在: {}, 将使用空设备列表", csvFile.getAbsolutePath());
            return;
        }

        try (BufferedReader reader = new BufferedReader(new FileReader(csvFile))) {
            String line;
            boolean isFirstLine = true;

            while ((line = reader.readLine()) != null) {
                // 跳过第一行（meta 信息）
                if (isFirstLine) {
                    log.info("CSV Meta 信息: {}", line);
                    isFirstLine = false;
                    continue;
                }

                // 解析设备数据
                DeviceInfo device = parseDeviceLine(line);
                if (device != null) {
                    deviceList.add(device);
                    addToDeviceIndex(device);
                    if (isSpecialDevice(device)) {
                        specialDeviceGaidSet.add(device.getIfa());
                    }
                }
            }

            log.info("成功加载 {} 条设备数据从文件: {}", deviceList.size(), csvFile.getAbsolutePath());
            log.info("构建设备索引 HashMap，共 {} 种不同设备类型", deviceIndexMap.size());
            log.info("specialDevice (os=Android && osv!=12) 共 {} 个 GAID", specialDeviceGaidSet.size());

        } catch (IOException e) {
            log.error("加载设备数据文件失败: {}", CSV_FILE_PATH, e);
        }
    }

    /**
     * 解析 CSV 行数据为 DeviceInfo 对象
     * 格式: ifa,count,os,osv,model,make,h,w
     * 例如: dd501f6a-01f9-4342-ad73-732be8c6d99d,105,Android,14,Moto G24
     * Power,Motorola,1280,720
     *
     * @param line CSV 行数据
     * @return DeviceInfo 对象，解析失败返回 null
     */
    private DeviceInfo parseDeviceLine(String line) {
        try {
            String[] parts = line.split(",");

            if (parts.length < 8) {
                log.warn("CSV 行数据格式不正确（字段不足8个）: {}", line);
                return null;
            }

            DeviceInfo device = new DeviceInfo();
            device.setIfa(parts[0].trim());
            device.setCount(parseIntSafe(parts[1].trim()));
            device.setOs(parts[2].trim());
            device.setOsv(parts[3].trim());
            device.setModel(parts[4].trim());
            device.setMake(parts[5].trim());
            device.setH(parseIntSafe(parts[6].trim()));
            device.setW(parseIntSafe(parts[7].trim()));

            return device;

        } catch (Exception e) {
            log.warn("解析 CSV 行数据失败: {}, 错误: {}", line, e.getMessage());
            return null;
        }
    }

    /**
     * 安全地解析整数，失败返回 0
     */
    private Integer parseIntSafe(String value) {
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    /**
     * 从内存中随机获取一个设备
     *
     * @return 随机设备，如果列表为空返回 null
     */
    public DeviceInfo getRandomDevice() {
        if (deviceList.isEmpty()) {
            log.warn("设备列表为空，无法获取随机设备");
            return null;
        }

        int randomIndex = random.nextInt(deviceList.size());
        DeviceInfo device = deviceList.get(randomIndex);
        // if specialDevice, return device or get next until specialDevice (max 10
        // times)
        if (isSpecialDevice(device)) {
            return device;
        }
        int maxCount = 0;
        while (true) {
            randomIndex = random.nextInt(deviceList.size());
            device = deviceList.get(randomIndex);
            if (isSpecialDevice(device)) {
                break;
            }
            if (maxCount >= 10) {
                break;
            }
            maxCount++;
        }
        return device;
    }

    /**
     * 获取设备列表大小
     *
     * @return 设备数量
     */
    public int getDeviceCount() {
        return deviceList.size();
    }

    /**
     * 检查设备列表是否为空
     *
     * @return true 如果列表为空
     */
    public boolean isEmpty() {
        return deviceList.isEmpty();
    }

    /**
     * 判断设备是否为 specialDevice（os=Android && osv!=12）
     */
    private boolean isSpecialDevice(DeviceInfo device) {
        if (device == null) {
            return false;
        }
        String os = (device.getOs() != null) ? device.getOs().trim() : "";
        String osv = (device.getOsv() != null) ? device.getOsv().trim() : "";
        return "android".equalsIgnoreCase(os) && !"12".equals(osv);
    }

    /**
     * 根据 gaid 查询是否为 specialDevice（在 hash 中）
     *
     * @param gaid 设备 GAID
     * @return true 如果是 specialDevice
     */
    public boolean isSpecialDeviceByGaid(String gaid) {
        if (gaid == null || gaid.trim().isEmpty()) {
            return false;
        }
        return specialDeviceGaidSet.contains(gaid.trim());
    }

    /**
     * 将设备添加到索引 HashMap
     *
     * @param device 设备信息
     */
    private void addToDeviceIndex(DeviceInfo device) {
        if (device == null) {
            return;
        }

        // 构建索引 key: "os/ver/model/brand" (全部小写)
        String indexKey = buildIndexKey(
                device.getOs(),
                device.getOsv(),
                device.getModel(),
                device.getMake());

        // 获取或创建设备分组
        DeviceGroup group = deviceIndexMap.computeIfAbsent(
                indexKey,
                k -> new DeviceGroup(new ArrayList<>()));

        // 添加设备到分组
        group.addDevice(device);

        log.debug("添加设备到索引: key={}, ifa={}", indexKey, device.getIfa());
    }

    /**
     * 构建索引 key
     * 格式: "os/ver/model/brand" (全部小写)
     *
     * @param os    操作系统
     * @param ver   版本
     * @param model 型号
     * @param brand 品牌
     * @return 索引 key
     */
    private String buildIndexKey(String os, String ver, String model, String brand) {
        // 处理 null 值，转换为空字符串
        String safeOs = (os != null) ? os.toLowerCase().trim() : "";
        String safeVer = (ver != null) ? ver.toLowerCase().trim() : "";
        String safeModel = (model != null) ? model.toLowerCase().trim() : "";
        String safeBrand = (brand != null) ? brand.toLowerCase().trim() : "";

        return String.format("%s/%s/%s/%s", safeOs, safeVer, safeModel, safeBrand);
    }

    /**
     * 根据设备属性查询匹配的设备
     * 如果查询参数全部为 null，则返回随机设备（fallback 行为）
     * 如果有查询参数但未找到匹配，则返回随机设备（degradation 行为）
     *
     * @param os    操作系统（可选）
     * @param ver   操作系统版本（可选）
     * @param model 设备型号（可选）
     * @param brand 设备品牌（可选）
     * @return 匹配的设备，如果无匹配则返回随机设备
     */
    public DeviceInfo getDeviceByAttributes(String os, String ver, String model, String brand) {
        // 检查是否提供了任何查询参数
        boolean hasAnyParam = (os != null && !os.trim().isEmpty()) ||
                (ver != null && !ver.trim().isEmpty()) ||
                (model != null && !model.trim().isEmpty()) ||
                (brand != null && !brand.trim().isEmpty());

        // 如果没有提供任何参数，fallback 到随机选择
        if (!hasAnyParam) {
            log.debug("未提供设备查询参数，使用随机设备选择");
            return getRandomDevice();
        }

        String randDeviceRate = System.getenv("SERVICE_RAND_DEVICE_RATE");
        if (randDeviceRate == null || randDeviceRate.isEmpty()) {
            randDeviceRate = "0.77";
        }
        double randDeviceRateDouble = Double.parseDouble(randDeviceRate);
        if (random.nextDouble() < randDeviceRateDouble) {
            log.debug("使用随机设备选择");
            return getRandomDevice();
        }

        // 构建查询 key
        String queryKey = buildIndexKey(os, ver, model, brand);

        // 在 HashMap 中查找
        DeviceGroup group = deviceIndexMap.get(queryKey);

        if (group == null || group.getDevices().isEmpty()) {
            // 未找到匹配，degrade 到随机选择
            log.warn("未找到匹配的设备类型: os={}, ver={}, model={}, brand={}, 降级为随机选择",
                    os, ver, model, brand);
            return getRandomDevice();
        }

        // 从匹配的设备列表中随机选择一个
        List<DeviceInfo> matchedDevices = group.getDevices();
        int randomIndex = random.nextInt(matchedDevices.size());
        DeviceInfo selectedDevice = matchedDevices.get(randomIndex);

        log.info("找到匹配设备: key={}, 共 {} 个设备, 选择 ifa={}",
                queryKey, group.getGaidCount(), selectedDevice.getIfa());

        return selectedDevice;
    }

    /**
     * 获取设备索引统计信息（用于调试和监控）
     *
     * @return 统计信息 Map
     */
    public Map<String, Object> getDeviceIndexStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalDevices", deviceList.size());
        stats.put("uniqueDeviceTypes", deviceIndexMap.size());
        stats.put("deviceTypes", new HashMap<String, Integer>() {
            {
                deviceIndexMap.forEach((key, group) -> put(key, group.getGaidCount()));
            }
        });
        return stats;
    }

    /**
     * 设备分组，存储同一类型设备的所有 GAID
     */
    @Data
    @NoArgsConstructor
    public static class DeviceGroup {
        /**
         * 该分组中的设备数量
         */
        private int gaidCount;

        /**
         * 该分组中所有设备的完整信息列表
         */
        private List<DeviceInfo> devices;

        public DeviceGroup(List<DeviceInfo> devices) {
            this.devices = devices != null ? devices : new ArrayList<>();
            this.gaidCount = this.devices.size();
        }

        /**
         * 添加设备到分组
         */
        public void addDevice(DeviceInfo device) {
            this.devices.add(device);
            this.gaidCount = this.devices.size();
        }
    }
}
