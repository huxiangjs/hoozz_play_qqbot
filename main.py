#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from fastmcp import Client
import threading
import queue
import json
import argparse
import os
import sys
import time
import botpy # pip install qq-botpy
from botpy.message import DirectMessage, Message
from botpy.ext.cog_yaml import read
from botpy.message import C2CMessage
from botpy.manage import C2CManageEvent
import json

parser = argparse.ArgumentParser(description='Hoozz Play QQ Bot')
parser.add_argument('--mcp_url', type=str, required=False, help='MCP url')
parser.add_argument('--std', action="store_true", required=False, help='Using standard input and output')
parser.add_argument('--config', type=str, required=False, help='Path to the YAML configuration file')
parser.add_argument('--qq_appid', type=str, required=False, help='QQ appid')
parser.add_argument('--qq_secret', type=str, required=False, help='QQ secret')
args = parser.parse_args()

qq_appid = None
qq_secret = None
mcp_url = None

config_file = args.config if args.config else os.path.join(os.path.dirname(__file__), "config.yaml")
try:
    config = read(config_file)
    if 'appid' in config:
        qq_appid = config['appid']
    if 'secret' in config:
        qq_secret = config['secret']
    if 'mcp' in config:
        mcp_url = config['mcp']
except:
    pass

use_std = True if args.std else False

if args.mcp_url:
    mcp_url = args.mcp_url
elif mcp_url is None:
    mcp_url = 'http://localhost:8000/mcp'

if args.qq_appid:
    qq_appid = args.qq_appid

if args.qq_secret:
    qq_secret = args.qq_secret

if qq_appid is None or qq_secret is None or mcp_url is None:
    raise Exception('Invalid parameter')

class std_io(threading.Thread):
    '''Standard input and output'''

    def __init__(self):
        super().__init__()
        self._queue = queue.Queue(maxsize=0)

    def reset(self):
        while True:
            try:
                self._queue.get(block=False)
            except queue.Empty:
                break

    def run(self):
        print('thread running')
        try:
            self._queue.get(block=True)
        except Exception:
            pass
        print('thread exited')

    def stop(self):
        self._queue.put(None)
        self.join()

    def get(self):
        data = None
        try:
            data = input()
        except Exception:
            pass
        return data

    def put(self, data):
        print(data)

class QQBot(botpy.Client):
    '''QQ bot'''

    def __init__(self, recv_queue, send_queue):
        self._recv_queue = recv_queue
        self._send_queue = send_queue
        self._exit_queue = queue.Queue(maxsize=0)
        intents = botpy.Intents.all()
        super().__init__(
            intents=intents,
            # log_level=10 # DEBUG
        )

    def break_loop(self):
        self._exit_queue.put(None)

    async def _stop(self):
        await asyncio.to_thread(self._exit_queue.get)
        print('break loop')
        # raise KeyboardInterrupt()
        raise SystemExit()

    async def _get(self):
        def data_get():
            try:
                return self._send_queue.get(block=True, timeout=5)
            except queue.Empty:
                return 'timeout'
        return await asyncio.to_thread(data_get)

    async def _put(self, data):
        self._recv_queue.put(data)

    async def on_ready(self):
        print(f'robot [{self.robot.name}] on_ready')
        asyncio.create_task(self._stop())

    async def on_direct_message_create(self, message: DirectMessage):
        content = f'robot [{self.robot.name}] recv: {message.content}'
        print(content)
        await self.api.post_dms(
            guild_id=message.guild_id,
            content=content,
            msg_id=message.id,
        )

    async def on_group_at_message_create(self, message: Message):
        content = f'robot [{self.robot.name}] recv: {message.content}'
        print(content)

    async def on_at_message_create(self, message: Message):
        content = f'robot [{self.robot.name}] recv: {message.content}'
        print(content)
        if '/私信' in message.content:
            dms_payload = await self.api.create_dms(message.guild_id, message.author.id)
            await self.api.post_dms(
                dms_payload['guild_id'],
                content='hello',
                msg_id=message.id
            )

    async def on_friend_add(self, event: C2CManageEvent):
        print(f'{sys._getframe().f_code.co_name}: {str(event)}')
        await self.api.post_c2c_message(
            openid=event.openid,
            msg_type=0,
            event_id=event.event_id,
            content='hello',
        )

    async def on_friend_del(self, event: C2CManageEvent):
        print(f'{sys._getframe().f_code.co_name}: {str(event)}')

    async def on_c2c_msg_reject(self, event: C2CManageEvent):
        print(f'{sys._getframe().f_code.co_name}: {str(event)}')

    async def on_c2c_msg_receive(self, event: C2CManageEvent):
        print(f'{sys._getframe().f_code.co_name}: {str(event)}')

    async def on_c2c_message_create(self, message: C2CMessage):
        content = f'{message.timestamp} robot [{self.robot.name}] recv: \n' \
                  f'{message.content}\n' \
                  f'Attachments:\n' \
                  f'{json.dumps(eval(str(message.attachments)), indent=4, ensure_ascii=False)}'
        print(content)
        await self._put(message.content)
        content = await self._get()
        # Send plain text
        await message._api.post_c2c_message(
            openid=message.author.user_openid,
            msg_type=0, msg_id=message.id,
            content=content
        )

class qqbot_io(threading.Thread):
    '''QQ-Bot input and output'''

    def __init__(self, appid, secret):
        super().__init__()
        self._appid = appid
        self._secret = secret
        self._recv_queue = queue.Queue(maxsize=0)
        self._send_queue = queue.Queue(maxsize=0)
        self._qqbot = QQBot(self._recv_queue, self._send_queue)
        self._running = True

    def reset(self):
        while True:
            try:
                self._recv_queue.get(block=False)
            except queue.Empty:
                break
        while True:
            try:
                self._send_queue.get(block=False)
            except queue.Empty:
                break

    def run(self):
        print('thread running')
        while self._running:
            try:
                self._qqbot.run(appid=self._appid, secret=self._secret)
                if self._running:
                    time.sleep(10)
            except Exception as e:
                print(e)
        print('thread exited')

    def stop(self):
        self._running = False
        self._qqbot.break_loop()
        self._recv_queue.put(None)

    def get(self):
        while True:
            try:
                data = self._recv_queue.get(block=True, timeout=1)
                break
            except queue.Empty:
                pass
        return data

    def put(self, data):
        self._send_queue.put(data)

class mcp_client:
    '''MCP client'''

    def __init__(self, inout, mcp_url):
        self._inout = inout
        self._client = Client(mcp_url)

    async def _init(self):
        await asyncio.to_thread(self._inout.init)
        print('inout exited')

    async def _get(self):
        result = await asyncio.to_thread(self._inout.get)
        # print(result)
        return result

    async def _put(self, data):
        await asyncio.to_thread(self._inout.put, data)

    async def run(self):
        async with self._client:
            tools = await self._client.list_tools()
            print('All tools:')
            for t in tools:
                print(f'  {t.name}')

        dev_bind = {
            'simple_ctrl_button_led': [
                ['ON', self._dev_button_led_on],
                ['OFF', self._dev_button_led_off],
            ],
            'simple_ctrl_voice_led': [
                ['ON', self._dev_voice_led_on],
                ['OFF', self._dev_voice_led_off],
            ],
            'simple_ctrl_sensor': [
                ['__dynamic_init__', self._dev_sensor_get_value]
            ],
            'simple_ctrl_smart_ir': [
                ['__dynamic_init__', self._dev_smart_ir_get_key_list],
                ['__dynamic_op__', self._dev_smart_ir_press_key]
            ],
        }

        dev_list = [ ]

        while True:
            data = await self._get()
            args = data.split('.')
            top_sel = -1
            result = 'Unkown'
            try:
                top_sel = int(args[0])
            except:
                pass
            if top_sel >= 0 and top_sel < len(dev_list):
                dev_sel = dev_list[top_sel]
                dev_id = dev_sel[0]
                dev_args = dev_sel[3]
                try:
                    class_sel = dev_bind[dev_sel[2]]
                    sub_sel = int(args[1])
                    dynamic_init = None
                    dynamic_exe = None
                    for item in class_sel:
                        if item[0] == '__dynamic_init__':
                            dynamic_init = item[1]
                        elif item[0] == '__dynamic_op__':
                            dynamic_exe = item[1]
                    if dynamic_exe:
                        result = await dynamic_exe(dev_id, sub_sel, dev_args)
                    elif dynamic_init:
                        pass
                    else:
                        func = class_sel[sub_sel][1]
                        result = await func(dev_id, dev_args)
                except:
                    pass
            elif top_sel == -1:
                dev_list = await self._manager_list_available_dev()
                dev_list_str = ''
                for top_i, top in enumerate(dev_list):
                    # Top menu
                    dev_list_str += f'[{top_i}]: {top[1]}\n'
                    # Sub menu
                    if top[2] in dev_bind:
                        sub_menu = dev_bind[top[2]]
                        sub_menu_str = ''
                        dev_id = top[0]
                        dev_args = [ ]
                        for sub_i, sub in enumerate(sub_menu):
                            name = sub[0]
                            if name == '__dynamic_init__':
                                func = sub[1]
                                sub_menu_str += await func(dev_id, dev_args)
                            elif name == '__dynamic_op__':
                                pass
                            else:
                                sub_menu_str += f'  [{sub_i}]: {name}\n'
                        top[3] = dev_args
                        dev_list_str += sub_menu_str
                if len(dev_list_str):
                    dev_list_str = dev_list_str[:-1]
                result = dev_list_str
            await self._put(result)

    async def _manager_list_available_dev(self):
        '''List all available devices'''
        dev_list = [ ]
        async with self._client:
            try:
                result = await self._client.call_tool('manager_list_available_dev', { })
                # print(result)
                for item in result.content:
                    dev_info = json.loads(item.text)
                    device_id = dev_info['device_id']
                    device_name = dev_info['device_name']
                    class_name = dev_info['class_name']
                    dev_list.append([device_id, device_name, class_name, [ ]])
            except:
                pass
        return dev_list

    async def _dev_button_led_on(self, device_id, args):
        '''Turn on the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 255, 'green': 255, 'blue': 255}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_button_led_off(self, device_id, args):
        '''Turn off the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 0, 'green': 0, 'blue': 0}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_voice_led_on(self, device_id, args):
        '''Turn on the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 255, 'green': 255, 'blue': 255}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_voice_led_off(self, device_id, args):
        '''Turn off the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 0, 'green': 0, 'blue': 0}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_sensor_get_value(self, device_id, args):
        '''Get sensor data'''
        retval = ''
        async with self._client:
            try:
                result = await self._client.call_tool('dev_sensor_get_sensor_info', {'device_id': device_id})
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                sensor_info = ret_dict['sensor_info']
                query_list = [ ]
                for item in sensor_info:
                    sensor_name = item['sensor_name']
                    sensor_id = item['sensor_id']
                    sensor_type = item['sensor_type']
                    query_list.append({
                        'sensor_id': sensor_id,
                        'sensor_type': sensor_type
                    })
                result = await self._client.call_tool(
                    'dev_sensor_get_sensor_data',
                    {'device_id': device_id, 'query_list': query_list}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                data = ret_dict['data']
                data_dict = { }
                for item in data:
                    sensor_id = item['sensor_id']
                    sensor_type = item['sensor_type']
                    sensor_data = item['sensor_data']
                    if sensor_type not in data_dict:
                        data_dict[sensor_type] = { }
                    data_dict[sensor_type][sensor_id] = sensor_data
                for item in sensor_info:
                    sensor_name = item['sensor_name']
                    sensor_id = item['sensor_id']
                    sensor_type = item['sensor_type']
                    sensor_data = data_dict[sensor_type][sensor_id]
                    retval += f"  {sensor_name}{sensor_id}: {sensor_data}\n"
            except:
                pass
        return retval

    async def _dev_smart_ir_get_key_list(self, device_id, args):
        '''Get IR key list'''
        retval = ''
        async with self._client:
            try:
                result = await self._client.call_tool('dev_smart_ir_get_key_list', {'device_id': device_id})
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                # print(ret_dict)
                key_list = ret_dict['key_list']
                for index, value in enumerate(key_list):
                    retval += f"  [{index}]: {value}\n"
                    args.append(value)
            except:
                pass
        return retval

    async def _dev_smart_ir_press_key(self, device_id, key_index, args):
        '''Press IR key'''
        retval = 'Unkown'
        async with self._client:
            try:
                key_name = args[key_index]
                result = await self._client.call_tool(
                    'dev_smart_ir_press_key',
                    {'device_id': device_id, 'key_name': key_name}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

async def main(inout, mcp_url):
    inout.reset()
    client = mcp_client(inout, mcp_url)
    await client.run()

if __name__ == '__main__':
    if use_std:
        inout = std_io()
    else:
        inout = qqbot_io(qq_appid, qq_secret)
    inout.start()

    while True:
        try:
            # asyncio.run(main(inout, mcp_url))
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main(inout, mcp_url))
        except KeyboardInterrupt:
            print('program interrupted by user')
            break
        except Exception as e:
            print(f'Asyncio exited: {e}')
        finally:
            pass
    inout.stop()
    print('program exited')
