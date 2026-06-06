package com.leeyom.scaffold.enums;

import com.baomidou.mybatisplus.annotation.IEnum;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Getter;
import org.springframework.util.StringUtils;

/**
 * <p>
 * 操作系统类型
 * </p>
 *
 * @author luoxun
 * @date 2025-06-13
 */
@AllArgsConstructor
@Getter
@JsonFormat(shape = JsonFormat.Shape.OBJECT)
public enum OsEnum implements IEnum<String> {
    iOS("iOS", "IOS"),
    ANDROID("Android", "Android"),
    Windows("Windows", "Windows"),
    UNKNOWN("UNKNOWN", "UNKNOWN"),
    ;
    private String value;
    private String name;

    public static boolean isValid(String value) {
        for (OsEnum item : OsEnum.values()) {
            if (item.getValue().equalsIgnoreCase(value)) {
                return true;
            }
        }
        return false;
    }

    public static OsEnum parse(String value) {
        if (!StringUtils.isEmpty(value)) {
            for (OsEnum item : OsEnum.values()) {
                if (item.getValue().equalsIgnoreCase(value)) {
                    return item;
                }
            }
        }
        return UNKNOWN;
    }

}
