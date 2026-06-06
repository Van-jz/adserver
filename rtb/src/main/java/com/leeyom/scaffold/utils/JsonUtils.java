package com.leeyom.scaffold.utils;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class JsonUtils {

    private static final ObjectMapper mapper;

    static {
        mapper = new ObjectMapper();
        mapper.setSerializationInclusion(JsonInclude.Include.NON_EMPTY);
    }

    public static String Object2Json(Object object) {
        try {
            return mapper.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            log.error("get json string error.", e);
            return "";
        }
    }

    public static <T> T Json2Object(String json, Class<T> valueType) {
        JsonFactory jsonFactory = new JsonFactory();
        JsonParser jsonParser;
        try {
            jsonParser = jsonFactory.createParser(json);
            return mapper.readValue(jsonParser, valueType);
        } catch (Exception e) {
            log.error("init region utils fail.", e);
            throw new RuntimeException("JSON转对象失败");
        }
    }

}
