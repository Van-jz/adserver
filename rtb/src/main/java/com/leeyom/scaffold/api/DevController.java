package com.leeyom.scaffold.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.leeyom.scaffold.dto.DeviceInfo;
import com.leeyom.scaffold.dto.TaskInfo;
import com.leeyom.scaffold.factory.AdvertChoiceBidOnePer1000;
import com.leeyom.scaffold.service.DeviceDataService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * 根据ssp请求向广告平台竞价
 *
 * @author luoxun
 * @since 2025-05-20 09:17:37
 */
@RestController
@RequestMapping("dev/rtb")
@Slf4j
public class DevController {

    @Value("${logRootPath:}")
    private String logRootPath;

    @Value("${kwaiadsinfo.tasks:[]}")
    private String tasksJson;

    @Resource
    private AdvertChoiceBidOnePer1000 advertChoiceBidOnePer1000;

    @Resource
    private ObjectMapper objectMapper;

    @Resource
    private DeviceDataService deviceDataService;

    private final Random random = new Random();

    /**
     * refresh_prop 任务中注入 phone 参数的概率
     * phone 值格式: "model,make"，数据来源于 ifa_device.csv
     */
    private static final double REFRESH_PROP_PHONE_RATE = 0.5;

    private static final String[] PRODUCT_NAMES = { "Samsung Galaxy S23 Ultra",
            "Samsung Galaxy S24 Ultra", "Samsung Galaxy S25 Ultra", "Samsung Galaxy S26 Ultra",
            "Samsung Galaxy S27 Ultra", "Samsung Galaxy S28 Ultra", "Samsung Galaxy S29 Ultra",
            "Samsung Galaxy S30 Ultra", "Galaxy S25", "Galaxy S25+", "Galaxy S25 Ultra",
            "Galaxy S24", "Galaxy S24+", "Galaxy S24 Ultra", "Galaxy S23+", "Galaxy Z Fold7",
            "Galaxy Z Flip7", "Galaxy Z Flip7 FE", "Galaxy A56 5G", "Galaxy A55 5G",
            "Galaxy A54 5G", "Galaxy A36 5G", "Galaxy A16 5G", "Galaxy A15 5G", "Galaxy A26 5G",
            "Galaxy A14 5G", "Galaxy W26", "Galaxy W25 Flip" };

    @GetMapping("/change/interval/{interval}")
    public ResponseEntity<Boolean> changeInterval(@PathVariable("interval") Integer interval) {
        advertChoiceBidOnePer1000.setINTERVAL(interval);
        return new ResponseEntity<>(true, HttpStatus.OK);
    }

    /**
     * 获取默认设备信息
     * 当 CSV 文件不存在或无法加载时使用
     */
    private DeviceInfo getDefaultDevice() {
        DeviceInfo defaultDevice = new DeviceInfo();
        defaultDevice.setIfa("c63673ad-5e2b-4e7e-b156-131fb3b4d0e5");
        defaultDevice.setCount(0);
        defaultDevice.setOs("Android");
        defaultDevice.setOsv("14");
        defaultDevice.setModel("SM-G998B");
        defaultDevice.setMake("Samsung");
        defaultDevice.setH(2400);
        defaultDevice.setW(1080);
        return defaultDevice;
    }

    @GetMapping("/trafficConfig")
    public ResponseEntity<Map<String, Object>> getTrafficConfig(
            @RequestParam(value = "gaid", required = false) String gaid,
            @RequestParam(value = "os", required = false) String os,
            @RequestParam(value = "ver", required = false) String ver,
            @RequestParam(value = "model", required = false) String model,
            @RequestParam(value = "brand", required = false) String brand) {
        // 记录所有请求参数
        log.info("trafficConfig request - gaid={}, os={}, ver={}, model={}, brand={}",
                gaid, os, ver, model, brand);

        // 根据设备属性查询设备（支持 fallback 和 degradation）
        DeviceInfo selectedDevice = deviceDataService.getDeviceByAttributes(os, ver, model, brand);

        // 如果查询结果为 null，使用默认设备
        if (selectedDevice == null) {
            selectedDevice = getDefaultDevice();
            log.warn("设备查询返回 null，使用默认设备 ifa={}", selectedDevice.getIfa());
        }

        // 记录设备选择路径（用于监控和调试）
        String selectionPath = determineSelectionPath(os, ver, model, brand, selectedDevice);
        log.info("设备选择路径: {}, 最终设备: ifa={}, os={}, osv={}, model={}, make={}",
                selectionPath, selectedDevice.getIfa(), selectedDevice.getOs(),
                selectedDevice.getOsv(), selectedDevice.getModel(), selectedDevice.getMake());

        // 原始配置数据 - 使用标准参数集合
        Map<String, Object> config = new HashMap<>();

        // 设置新的 gaid（使用选择的设备的 ifa）
        String initGaid = "d55673ad-5e2b-4e7e-b156-131fb3b4d0e5";
        config.put("gaid", selectedDevice.getIfa());

        // 设备属性 需要重启app才能生效
        String productName = PRODUCT_NAMES[random.nextInt(PRODUCT_NAMES.length)];
        if (random.nextDouble() < 0.1) {
            productName += " " + random.nextInt(100);
        }
        config.put("prop.ro.product.name", productName);
        //CRITICAL: 如果增加这几个属性，当前会导致客户端异常
        //config.put("prop.ro.product.brand", selectedDevice.getMake());
        //config.put("prop.ro.product.model", selectedDevice.getModel());
        //config.put("prop.ro.product.manufacturer", selectedDevice.getMake());
        /*
         * config.put("prop.ro.settings.android_id", "9774d56d682e54cc");
         * config.put("prop.ro.settings.device_name", randomDevice.getModel());
         * 
         * // 网络信息
         * config.put("net.wifi.enabled", true);
         * config.put("net.wifi.connected", true);
         * config.put("net.wifi.ssid", "MyWiFi_BR");
         * config.put("net.wifi.ipaddress", "192.168.1.100");
         * config.put("net.cm.type", 1);
         * config.put("net.cm.typeName", "WIFI");
         * config.put("net.if.mac", "02:00:00:00:00:00");
         * 
         * // GPS位置 - 巴西圣保罗（添加随机扰动）
         * // 基准坐标：圣保罗市中心
         * double baseLat = -23.5505;
         * double baseLon = -46.6333;
         * // 添加随机偏移（±0.05度，约±5.5公里），保持在圣保罗市内
         * double latOffset = (random.nextDouble() - 0.5) * 0.1; // [-0.05, 0.05]
         * double lonOffset = (random.nextDouble() - 0.5) * 0.1; // [-0.05, 0.05]
         * double randomLat = roundToFourDecimals(baseLat + latOffset);
         * double randomLon = roundToFourDecimals(baseLon + lonOffset);
         * // 精度随机：5.0 到 20.0 米
         * float randomAccuracy = 5.0f + random.nextFloat() * 15.0f;
         * 
         * config.put("location.lat", randomLat);
         * config.put("location.lon", randomLon);
         * config.put("location.accuracy", roundToTwoDecimals(randomAccuracy));
         * config.put("location.mock", false);
         * 
         * // SIM卡信息 - 巴西运营商
         * config.put("sim.state", 5);
         * config.put("sim.imei", "351234567890123");
         * config.put("sim.operatorLongName", "Claro BR");
         * config.put("sim.operatorShortName", "Claro");
         * config.put("sim.numeric", "72405");
         * config.put("sim.tm.networkType", 13);
         * config.put("sim.tm.isNetworkRoaming", false);
         * config.put("sim.tm.networkCountryIso", "br");
         * config.put("sim.tm.simState", 5);
         * 
         * // 电池信息
         * config.put("battery.batteryLevel", 85);
         * config.put("battery.batteryStatus", 2);
         * config.put("battery.chargerAcOnline", 0);
         * 
         * // 显示信息
         * config.put("display.name", randomDevice.getMake() + " Display");
         * 
         * // 系统信息
         * config.put("system.su", false);
         * 
         * // 添加设备的 os、osv、h、w 信息
         * config.put("device.os", randomDevice.getOs());
         * config.put("device.osv", randomDevice.getOsv());
         * config.put("device.h", randomDevice.getH());
         * config.put("device.w", randomDevice.getW());
         * config.put("device.model", randomDevice.getModel());
         * config.put("device.make", randomDevice.getMake());
         */

        // 转换为 props 数组格式
        List<Map<String, Object>> props = new ArrayList<>();
        for (Map.Entry<String, Object> entry : config.entrySet()) {
            Map<String, Object> prop = new HashMap<>();
            prop.put("key", entry.getKey());
            prop.put("value", entry.getValue());
            props.add(prop);
        }

        // 封装标准响应格式
        Map<String, Object> response = new HashMap<>();
        response.put("code", 200);
        response.put("message", "OK");
        Map<String, Object> data = new HashMap<>();
        data.put("props", props);
        response.put("data", data);

        return new ResponseEntity<>(response, HttpStatus.OK);
    }

    @GetMapping("/kwaiadsinfo/tasks")
    public ResponseEntity<Map<String, Object>> getTasks(
            @RequestParam(value = "gaid", required = false) String gaid,
            @RequestParam(value = "ctr_factor", required = false, defaultValue = "1.0") double ctrFactor) {
        List<TaskInfo> tasks;

        // gaid 不空且为 specialDevice 时，返回精简任务列表
        if (gaid != null && !gaid.trim().isEmpty() && deviceDataService.isSpecialDeviceByGaid(gaid)) {
            tasks = getSpecialDeviceTasks();
            log.info("specialDevice gaid={}, 返回精简任务列表，共 {} 个任务", gaid, tasks.size());
        } else {
            try {
                // 从配置的 JSON 字符串解析任务列表
                tasks = objectMapper.readValue(tasksJson, new TypeReference<List<TaskInfo>>() {
                });
                log.info("成功从配置解析任务列表，共 {} 个任务", tasks.size());
            } catch (Exception e) {
                // 如果解析失败，返回空列表或使用默认值
                tasks = getDefaultTasks(ctrFactor);
                log.info("使用默认任务列表，ctr_factor={}, 共 {} 个任务", ctrFactor, tasks.size());
            }
            // 对 click_ad 任务应用随机偏移
            applyRandomOffset(tasks);
        }

        // 封装标准响应格式
        Map<String, Object> response = new HashMap<>();
        response.put("code", 200);
        response.put("message", "OK");
        Map<String, Object> data = new HashMap<>();
        data.put("tasks", tasks);
        response.put("data", data);

        return new ResponseEntity<>(response, HttpStatus.OK);
    }

    /**
     * 构建 refresh_prop 任务的参数：
     * 按 {@link #REFRESH_PROP_PHONE_RATE} 概率从 ifa_device.csv 随机取一台设备，
     * 注入 phone=model,make（例如 "SM-A032M,samsung"）。
     */
    private Map<String, Object> buildRefreshPropParams() {
        Map<String, Object> params = new HashMap<>();
        if (random.nextDouble() >= REFRESH_PROP_PHONE_RATE) {
            return params;
        }
        DeviceInfo device = deviceDataService.getRandomDevice();
        if (device == null) {
            return params;
        }
        String model = device.getModel();
        String make = device.getMake();
        if (model == null || model.trim().isEmpty() || make == null || make.trim().isEmpty()) {
            return params;
        }
        String phone = model.trim() + "," + make.trim();
        params.put("phone", phone);
        log.debug("refresh_prop 注入 phone 参数: {}", phone);
        return params;
    }

    /**
     * specialDevice 精简任务列表：1个 refresh_prop，1个 click_load(repeat:3,
     * inner_delay:90)，1个 restart_app
     */
    private List<TaskInfo> getSpecialDeviceTasks() {
        List<TaskInfo> tasks = new ArrayList<>();
        tasks.add(new TaskInfo("refresh_prop", buildRefreshPropParams(), null, 2000));
        Map<String, Object> clickLoadParams = new HashMap<>();
        clickLoadParams.put("repeat", 3);
        clickLoadParams.put("inner_delay", 90);
        tasks.add(new TaskInfo("click_load", clickLoadParams, null, 1000));
        tasks.add(new TaskInfo("restart_app", new HashMap<>(), null, 2000));
        return tasks;
    }

    /**
     * 获取默认任务列表（用于配置解析失败时的备用方案）
     */
    private List<TaskInfo> getDefaultTasks(double ctrFactor) {
        List<TaskInfo> tasks = new ArrayList<>();

        tasks.add(new TaskInfo("refresh_prop", buildRefreshPropParams(), null, 2000));

        // 要跟SERVICE_RAND_DEVICE_RATE参数打配合
        int round = 2 + random.nextInt(6);
        for (int i = 0; i < round; i++) {
            tasks.addAll(getDefaultRound1Tasks(ctrFactor));
        }

        tasks.add(new TaskInfo("refresh_prop", buildRefreshPropParams(), null, 2000));
        tasks.add(new TaskInfo("restart_app", new HashMap<>(), null, 5000));
        return tasks;
    }

    // 大概20s一轮
    private List<TaskInfo> getDefaultRound1Tasks(double ctrFactor) {
        List<TaskInfo> tasks = new ArrayList<>();

        tasks.add(new TaskInfo("navigate_main", new HashMap<>(), null, 100));
        // tasks.add(new TaskInfo("navigate_Interstitial", new HashMap<>(), null, 500));

        // 使用 repeat 和 inner_delay 参数替代循环
        Map<String, Object> clickLoadParams = new HashMap<>();
        clickLoadParams.put("repeat", 30);
        clickLoadParams.put("inner_delay", 90); // 客户端每次会自动XXX ms+random(90)
        tasks.add(new TaskInfo("click_load", clickLoadParams, null, 2000 + random.nextInt(1000)));

        // 示例任务5: 点击显示， 客户端保证前面有广告加载成功后才会执行此任务
        tasks.add(new TaskInfo("click_show", new HashMap<>(), null, 2000 + random.nextInt(800)));

        // 示例任务6: 点击广告 - 客户端使用默认坐标值
        if (random.nextDouble() < 0.2 * ctrFactor) {
            tasks.add(new TaskInfo("click_ad", new HashMap<>(), null, 5000 + random.nextInt(10000)));
        }

        return tasks;
    }

    /**
     * 对 click_ad 任务应用随机 delay 偏移
     * delay 的随机偏移范围: [0, 5000]
     */
    private void applyRandomOffset(List<TaskInfo> tasks) {
        for (TaskInfo task : tasks) {
            if ("click_ad".equals(task.getTargetElement())) {
                // 处理 delay 偏移
                if (task.getDelay() != null) {
                    Integer originalDelay = task.getDelay();
                    // delay 的随机偏移范围: [0, 5000]
                    int delayOffset = random.nextInt(5001);
                    int newDelay = originalDelay + delayOffset;
                    task.setDelay(newDelay);

                    log.debug("click_ad delay 随机偏移: 原始({}) -> 偏移({}) -> 最终({})",
                            originalDelay, delayOffset, newDelay);
                }
            }
        }
    }

    /**
     * 保留两位小数
     */
    private float roundToTwoDecimals(float value) {
        BigDecimal bd = new BigDecimal(Float.toString(value));
        bd = bd.setScale(2, RoundingMode.HALF_UP);
        return bd.floatValue();
    }

    /**
     * 保留四位小数（用于 GPS 坐标）
     */
    private double roundToFourDecimals(double value) {
        BigDecimal bd = new BigDecimal(Double.toString(value));
        bd = bd.setScale(4, RoundingMode.HALF_UP);
        return bd.doubleValue();
    }

    /**
     * 接收 kwaiadsinfo postshow 数据并打印到日志
     * 支持 GET 和 POST 两种方法
     */
    @RequestMapping(value = "/kwaiadsinfo/postshow", method = { RequestMethod.GET, RequestMethod.POST })
    public ResponseEntity<Map<String, Object>> postShowData(
            @RequestBody(required = false) String requestBody,
            @RequestParam(required = false) String data) {

        // 优先使用 POST body，如果没有则使用 GET 参数
        String actualData = requestBody != null ? requestBody : data;

        if (actualData != null && !actualData.isEmpty()) {
            log.info("收到 kwaiadsinfo postshow 请求数据: {}", actualData);
        } else {
            log.warn("收到 kwaiadsinfo postshow 请求，但没有数据");
        }

        // 封装标准响应格式
        Map<String, Object> response = new HashMap<>();
        response.put("code", 200);
        response.put("message", "OK");
        response.put("data", new HashMap<>());

        return new ResponseEntity<>(response, HttpStatus.OK);
    }

    /**
     * 确定设备选择路径（用于日志和监控）
     *
     * @return 选择路径描述
     */
    private String determineSelectionPath(String os, String ver, String model, String brand,
            DeviceInfo selectedDevice) {
        boolean hasAnyParam = (os != null && !os.trim().isEmpty()) ||
                (ver != null && !ver.trim().isEmpty()) ||
                (model != null && !model.trim().isEmpty()) ||
                (brand != null && !brand.trim().isEmpty());

        if (!hasAnyParam) {
            return "FALLBACK_RANDOM (no parameters provided)";
        }

        // 检查是否精确匹配
        boolean exactMatch = matchesDevice(selectedDevice, os, ver, model, brand);

        if (exactMatch) {
            return "EXACT_MATCH (targeted selection)";
        } else {
            return "DEGRADED_RANDOM (no match found, fallback to random)";
        }
    }

    /**
     * 检查设备是否与查询参数匹配
     */
    private boolean matchesDevice(DeviceInfo device, String os, String ver, String model, String brand) {
        if (device == null) {
            return false;
        }

        boolean osMatch = (os == null || os.trim().isEmpty() ||
                os.trim().equalsIgnoreCase(device.getOs()));
        boolean verMatch = (ver == null || ver.trim().isEmpty() ||
                ver.trim().equalsIgnoreCase(device.getOsv()));
        boolean modelMatch = (model == null || model.trim().isEmpty() ||
                model.trim().equalsIgnoreCase(device.getModel()));
        boolean brandMatch = (brand == null || brand.trim().isEmpty() ||
                brand.trim().equalsIgnoreCase(device.getMake()));

        return osMatch && verMatch && modelMatch && brandMatch;
    }

    /**
     * 获取设备索引统计信息（调试端点）
     */
    @GetMapping("/deviceIndexStats")
    public ResponseEntity<Map<String, Object>> getDeviceIndexStats() {
        Map<String, Object> stats = deviceDataService.getDeviceIndexStats();

        Map<String, Object> response = new HashMap<>();
        response.put("code", 200);
        response.put("message", "OK");
        response.put("data", stats);

        return new ResponseEntity<>(response, HttpStatus.OK);
    }

}
