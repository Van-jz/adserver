package com.leeyom.scaffold.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultHandlers.print;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * DevController 单元测试
 *
 * @author luoxun
 * @since 2025-11-04
 */
@SpringBootTest
@AutoConfigureMockMvc
class DevControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void testGetTrafficConfig_ReturnsValidJson() throws Exception {
        // 执行GET请求
        MvcResult result = mockMvc.perform(get("/dev/rtb/trafficConfig")
                        .contentType(MediaType.APPLICATION_JSON))
                .andDo(print())
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andReturn();

        // 解析返回的JSON
        String jsonResponse = result.getResponse().getContentAsString();
        Map<String, Object> response = objectMapper.readValue(jsonResponse, Map.class);

        // 验证响应结构
        assertNotNull(response, "响应不应为null");
        assertEquals(200, response.get("code"), "code应为200");
        assertEquals("OK", response.get("message"), "message应为OK");
        assertTrue(response.containsKey("data"), "应包含data字段");

        // 验证data结构
        Map<String, Object> data = (Map<String, Object>) response.get("data");
        assertNotNull(data, "data不应为null");
        assertTrue(data.containsKey("props"), "data应包含props字段");

        // 验证props数组
        List<Map<String, Object>> props = (List<Map<String, Object>>) data.get("props");
        assertNotNull(props, "props不应为null");
        assertEquals(28, props.size(), "props应包含28个配置项");

        // 将props转换为Map便于验证
        Map<String, Object> configMap = new HashMap<>();
        for (Map<String, Object> prop : props) {
            assertTrue(prop.containsKey("key"), "每个prop应包含key字段");
            assertTrue(prop.containsKey("value"), "每个prop应包含value字段");
            configMap.put((String) prop.get("key"), prop.get("value"));
        }

        // 验证所有必需的字段都存在（新的参数集合）
        String[] requiredKeys = {
            "prop.ro.serialno", "prop.ro.settings.android_id", "prop.ro.settings.device_name",
            "net.wifi.enabled", "net.wifi.connected", "net.wifi.ssid", "net.wifi.ipaddress",
            "net.cm.type", "net.cm.typeName", "net.if.mac",
            "sim.state", "sim.imei", "sim.operatorLongName", "sim.operatorShortName",
            "sim.numeric", "sim.tm.networkType", "sim.tm.isNetworkRoaming",
            "sim.tm.networkCountryIso", "sim.tm.simState",
            "location.lat", "location.lon", "location.accuracy", "location.mock",
            "battery.batteryLevel", "battery.batteryStatus", "battery.chargerAcOnline",
            "display.name", "system.su"
        };
        for (String key : requiredKeys) {
            assertTrue(configMap.containsKey(key), "应包含字段: " + key);
        }

        // 验证特定值和类型
        assertEquals("ABC123DEF456", configMap.get("prop.ro.serialno"), "prop.ro.serialno应为ABC123DEF456");
        assertEquals(true, configMap.get("net.wifi.enabled"), "net.wifi.enabled应为true");
        assertEquals(1, configMap.get("net.cm.type"), "net.cm.type应为1");
        assertEquals("Claro BR", configMap.get("sim.operatorLongName"), "sim.operatorLongName应为Claro BR");
        assertEquals(5, configMap.get("sim.state"), "sim.state应为5");
        assertEquals(false, configMap.get("sim.tm.isNetworkRoaming"), "sim.tm.isNetworkRoaming应为false");
        assertEquals(-23.5505, configMap.get("location.lat"), "location.lat应为-23.5505");
        assertEquals(false, configMap.get("location.mock"), "location.mock应为false");
        assertEquals(85, configMap.get("battery.batteryLevel"), "battery.batteryLevel应为85");

        System.out.println("✅ JSON验证通过！返回格式符合标准响应结构，包含28个标准配置参数");
        System.out.println("📊 返回的JSON: " + jsonResponse);
    }

    @Test
    void testGetTrafficConfig_JsonStructure() throws Exception {
        mockMvc.perform(get("/dev/rtb/trafficConfig"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("OK"))
                .andExpect(jsonPath("$.data").exists())
                .andExpect(jsonPath("$.data.props").isArray())
                .andExpect(jsonPath("$.data.props.length()").value(28))
                .andExpect(jsonPath("$.data.props[?(@.key=='prop.ro.serialno')].value").value("ABC123DEF456"))
                .andExpect(jsonPath("$.data.props[?(@.key=='net.wifi.enabled')].value").value(true))
                .andExpect(jsonPath("$.data.props[?(@.key=='sim.operatorLongName')].value").value("Claro BR"))
                .andExpect(jsonPath("$.data.props[?(@.key=='location.lat')].value").value(-23.5505))
                .andExpect(jsonPath("$.data.props[?(@.key=='system.su')].value").value(false));
    }
}
