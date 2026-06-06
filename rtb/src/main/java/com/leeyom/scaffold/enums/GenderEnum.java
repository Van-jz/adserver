package com.leeyom.scaffold.enums;

import com.baomidou.mybatisplus.annotation.IEnum;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Getter;
import org.springframework.util.StringUtils;

/**
 * <p>
 * 性别
 * </p>
 *
 * @author luoxun
 * @date 2025-06-13
 */
@AllArgsConstructor
@Getter
@JsonFormat(shape = JsonFormat.Shape.OBJECT)
public enum GenderEnum implements IEnum<String> {

    MALE("M", "男"),
    FEMALE("F", "女"),
    KNOWN("O", "已知"),
    UNKNOWN("UNKNOWN", "未知"),
    ;
    private String value;
    private String name;

    public static boolean isValid(String value) {
        for (GenderEnum item : GenderEnum.values()) {
            if (item.getValue().equalsIgnoreCase(value)) {
                return true;
            }
        }
        return false;
    }

    public static GenderEnum parse(String value) {
        if (!StringUtils.isEmpty(value)) {
            for (GenderEnum item : GenderEnum.values()) {
                if (item.getValue().equalsIgnoreCase(value)) {
                    return item;
                }
            }
        }
        return UNKNOWN;
    }

}
