package.path = package.path .. '/usr/share/lua/5.1/?.lua;' 

local function lease()

	local ldict = {}
	local lmess = {}

	local function store_lease(hash, ip_and_port_str)
	    ldict[hash] = ip_and_port_str
	    return true	
        end

	local function get_lease(hash)
	    return ldict[hash]
	end

	local function want_connect(hash, ip_and_port_str)
	    if ldict[hash] then
		if not lmess[hash] then
	    	    lmess[hash] = ip_and_port_str
		    return "Sent" 
		else
		    return "Ret"
		end
	    end
	end

	local function who_wanted_connect(hash)
	    if lmess[hash] then
		    ret = lmess[hash]
		    lmess[hash] = nil
	    	return ret 
	    else
		return ""
	    end
	end

	local function cmd_worker(cmds, value, ip, port)
	    if cmds == "set" or cmds == "setlease" then
	        store_lease(value, ip .. ":" .. port) 
		return value .. " registered " .. who_wanted_connect(value)
	    elseif cmds == "get" or cmds == "getlease" then
		return "client " .. value .. " " .. get_lease(value)
	    elseif cmds == "con" or cmds == "conn" then
		local ret = want_connect(value, ip .. ":" .. port)
		if ret then
		    return ret 
		else
		    return "NtC"
		end
	    end

	end

	return { store_lease=store_lease, get_lease=get_lease,
		cmd_worker=cmd_worker }

end

local socket = require("socket")
host = host or "192.168.2.6"
port = port or 8001 
if arg then
    host = arg[1] or host
    port = arg[2] or port
end
print("Binding to host '" ..host.. "' and port " ..port.. "...")
udp = assert(socket.udp())
assert(udp:setsockname(host, port))
assert(udp:settimeout(5))
ip, port = udp:getsockname()
assert(ip, port)
print("Waiting packets on " .. ip .. ":" .. port .. "...")

local l = lease()

while 1 do
	local dgram, ip, port = udp:receivefrom()
	if dgram then
	    local cmd, value = string.match(dgram, "(%a+)%s+(.*)$")
	    print("Got cmd: " .. dgram)
	    if cmd and value then
		local ret = l.cmd_worker(cmd, value, ip, port)
		if ret then
			udp:sendto(">" .. ret .. "\n", ip, port) 
		else
			udp:sendto(">" .. ip .. ":" .. port .. "\n", ip, port)
		end
	    else
		print(dgram) 
	    end
 	else
	    print(ip)
	end	
end
