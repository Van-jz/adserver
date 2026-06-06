package com.leeyom.scaffold.common.enums;

import lombok.Getter;

import java.util.stream.Stream;

/**
 * 通用状态枚举
 *
 * @author leeyom
 */
@Getter
public enum Status implements IStatus {
    /**
     * 操作成功！
     */
    SUCCESS(200, "success"),

    /**
     * 操作异常！
     */
    ERROR(500, "error"),

    /**
     * 退出成功！
     */
    LOGOUT(200, "log out success"),

    /**
     * 请先登录！
     */
    UNAUTHORIZED(401, "unauthorized"),

    /**
     * 暂无权限访问！
     */
    ACCESS_DENIED(403, "access denied"),

    /**
     * 请求不存在！
     */
    REQUEST_NOT_FOUND(404, "request not found"),

    /**
     * 请求方式不支持！
     */
    HTTP_BAD_METHOD(405, "http bad method"),

    /**
     * 请求异常！
     */
    BAD_REQUEST(400, "bad request"),

    /**
     * 参数不匹配！
     */
    PARAM_NOT_MATCH(400, "param not match"),

    /**
     * 参数不能为空！
     */
    PARAM_NOT_NULL(400, "param not null"),

    /**
     * 当前用户已被锁定，请联系管理员解锁！
     */
    USER_DISABLED(403, "user disabled"),

    /**
     * 用户名或密码错误！
     */
    USERNAME_PASSWORD_ERROR(5001, "username or password error"),

    /**
     * token 已过期，请重新登录！
     */
    TOKEN_EXPIRED(5002, "token expired"),

    /**
     * token 解析失败，请尝试重新登录！
     */
    TOKEN_PARSE_ERROR(5002, "token parse error"),

    /**
     * 当前用户已在别处登录，请尝试更改密码或重新登录！
     */
    TOKEN_OUT_OF_CTRL(5003, "token out of ctrl"),

    /**
     * 无法手动踢出自己，请尝试退出登录操作！
     */
    KICKOUT_SELF(5004, "kickout self");

    /**
     * 状态码
     */
    private Integer code;

    /**
     * 返回信息
     */
    private String message;

    Status(Integer code, String message) {
        this.code = code;
        this.message = message;
    }

    public static Status getStatusByCode(Integer code) {
        return Stream.of(Status.values()).filter(item -> item.getCode().equals(code)).findFirst().orElse(SUCCESS);
    }

    @Override
    public String toString() {
        return String.format(" Status:{code=%s, message=%s} ", getCode(), getMessage());
    }

}
